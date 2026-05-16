import logging
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from threading import Lock
from uuid import uuid4

from sqlalchemy import text
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import pandas as pd
from sqlalchemy.orm import Session
from src.db.session import engine, get_db

log = logging.getLogger(__name__)

router = APIRouter()

_EXPORT_QUERY = """
    SELECT
        "OBRA_PRONTO",
        "DESCRIPCION_OBRA",
        "FECHA",
        "FUENTE",
        "TIPO_COMPROBANTE",
        "NRO_COMPROBANTE",
        "PROVEEDOR",
        "DETALLE",
        "CODIGO_CUENTA",
        "IMPORTE",
        "OBSERVACION",
        "RUBRO_CONTABLE",
        "CUENTA_CONTABLE",
        "COMPENSABLE",
        "GERENCIA",
        "TC",
        "IMPORTE_USD"
    FROM fact_costos_b52
    ORDER BY "FECHA", "OBRA_PRONTO"
"""
_EXPORT_DIR = Path(tempfile.gettempdir()) / "pose_b52_exports"
_JOB_TTL_HOURS = 6
_jobs: dict[str, dict[str, str | int | None]] = {}
_jobs_lock = Lock()
_executor = ThreadPoolExecutor(max_workers=1)


def _cleanup_old_jobs() -> None:
    now = datetime.utcnow()
    expired: list[str] = []
    with _jobs_lock:
        for job_id, job in _jobs.items():
            created_raw = job.get("created_at")
            if not isinstance(created_raw, str):
                expired.append(job_id)
                continue
            created_at = datetime.fromisoformat(created_raw)
            if now - created_at > timedelta(hours=_JOB_TTL_HOURS):
                path_raw = job.get("file_path")
                if isinstance(path_raw, str):
                    file_path = Path(path_raw)
                    if file_path.exists():
                        file_path.unlink(missing_ok=True)
                expired.append(job_id)
        for job_id in expired:
            _jobs.pop(job_id, None)


def _run_excel_export_job(job_id: str) -> None:
    with _jobs_lock:
        if job_id not in _jobs:
            return
        _jobs[job_id]["status"] = "running"

    try:
        df = pd.read_sql(text(_EXPORT_QUERY), engine)
        _EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"b52_{date.today().isoformat()}_{job_id[:8]}.xlsx"
        file_path = _EXPORT_DIR / filename
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)

        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "done"
                _jobs[job_id]["file_path"] = str(file_path)
                _jobs[job_id]["filename"] = filename
                _jobs[job_id]["rows"] = int(len(df))
                _jobs[job_id]["error"] = None
    except Exception as exc:
        log.exception("Error generando export Excel b52 job=%s", job_id)
        with _jobs_lock:
            if job_id in _jobs:
                _jobs[job_id]["status"] = "error"
                _jobs[job_id]["error"] = str(exc)


def _create_export_job() -> str:
    _cleanup_old_jobs()
    job_id = uuid4().hex
    with _jobs_lock:
        _jobs[job_id] = {
            "status": "queued",
            "created_at": datetime.utcnow().isoformat(),
            "file_path": None,
            "filename": None,
            "rows": None,
            "error": None,
        }
    _executor.submit(_run_excel_export_job, job_id)
    return job_id


@router.get("/dashboard-data")
def get_dashboard_data(db: Session = Depends(get_db)):
    query = text("""
        SELECT
            substring(CAST(f."FECHA" AS VARCHAR) FROM 1 FOR 7) AS mes,
            COALESCE(d.gerencia, f."GERENCIA", '')             AS gerencia,
            f."IMPORTE"                                        AS importe
        FROM fact_costos_b52 f
        LEFT JOIN dim_obras_gerencias d
            ON f."OBRA_PRONTO" = d.obra_pronto
        WHERE f."FECHA" IS NOT NULL
    """)
    df = pd.read_sql(query, db.connection())

    meses_unicos = sorted(df["mes"].dropna().unique().tolist())

    df_mes = df.groupby("mes", as_index=False)["importe"].sum()
    monthly_summary = []
    for _, row in df_mes.iterrows():
        monthly_summary.append(
            {
                "mes": row["mes"],
                "ing_op": 0,
                "egr_op": float(row["importe"]),
                "egr_total": float(row["importe"]),
                "mop": 0,
                "amort": 0,
                "gasto_sede": 0,
                "me": float(row["importe"]),
                "pmo": 0,
                "pme": 0,
                "ing_fin": 0,
                "egr_fin": 0,
                "ing_nop": 0,
                "egr_nop": 0,
            }
        )

    gerencias_list = sorted(
        [g for g in df["gerencia"].dropna().unique().tolist() if g]
    )
    gerencias_monthly = {}
    for ger in gerencias_list:
        df_g = df[df["gerencia"] == ger]
        res_g = df_g.groupby("mes")["importe"].sum().to_dict()
        ger_dict = {}
        for m in meses_unicos:
            gasto = res_g.get(m, 0.0)
            if float(gasto) != 0.0:
                ger_dict[m] = {
                    "ing": 0,
                    "egr_excl": float(gasto),
                    "egr_total": float(gasto),
                    "amort": 0,
                    "gasto_sede": 0,
                    "mop": 0,
                    "pmo": 0,
                    "margen_final": float(gasto),
                    "pfinal": 0,
                    "egr": float(gasto),
                    "me": float(gasto),
                    "pme": 0,
                }
        gerencias_monthly[ger] = ger_dict

    # ── Obras con JOIN dim_obras_gerencias ────────────────────────────────
    obras: list[dict] = []
    obras_monthly: dict = {}
    try:
        q_obras = text("""
            SELECT
                f."OBRA_PRONTO"     AS obra_pronto,
                substring(CAST(f."FECHA" AS VARCHAR) FROM 1 FOR 7) AS mes,
                f."IMPORTE"         AS importe,
                COALESCE(d.descripcion_obra, f."DESCRIPCION_OBRA", '')
                    AS descripcion_obra,
                COALESCE(d.compensable, f."COMPENSABLE", '')
                    AS compensable,
                COALESCE(d.gerencia, f."GERENCIA", '') AS gerencia
            FROM fact_costos_b52 f
            LEFT JOIN dim_obras_gerencias d
                ON f."OBRA_PRONTO" = d.obra_pronto
            WHERE f."FECHA" IS NOT NULL
              AND f."OBRA_PRONTO" IS NOT NULL
        """)
        df_o = pd.read_sql(q_obras, db.connection())

        resumen = df_o.groupby("obra_pronto", as_index=False).agg(
            descripcion_obra=("descripcion_obra", "first"),
            compensable=("compensable", "first"),
            gerencia=("gerencia", "first"),
            total_importe=("importe", "sum"),
        )
        obras = [
            {
                "obra": row["obra_pronto"],
                "descripcion": row["descripcion_obra"],
                "gerencia": row["gerencia"],
                "compensable": row["compensable"],
                "total_importe": float(row["total_importe"]),
            }
            for _, row in resumen.iterrows()
        ]

        for obra_pronto, grupo in df_o.groupby("obra_pronto"):
            res_m = grupo.groupby("mes")["importe"].sum().to_dict()
            obras_monthly[str(obra_pronto)] = {
                m: {"importe": float(v)}
                for m, v in res_m.items()
                if float(v) != 0.0
            }
    except Exception as exc:
        log.warning("obras JOIN no disponible: %s", exc)

    return {
        "months": meses_unicos,
        "monthly_summary": monthly_summary,
        "gerencias_list": gerencias_list,
        "gerencias_all": gerencias_list,
        "gerencias_monthly": gerencias_monthly,
        "obras_monthly": obras_monthly,
        "obras": obras,
        "comp_empresas_monthly": {},
        "comp_empresas": {},
        "fuente_by_obra": {},
        "global_info": {
            "total_obras": 0,
            "total_gerencias": len(gerencias_list),
            "total_comp": 0,
        },
        "tipo_subtipo_map": {},
        "estados_list": [],
        "subtipos_list": [],
        "tipos_obra_list": [],
        "prov_fuentes": [],
        "tipos_cliente_list": [],
        "default_groups": [],
        "all_display_groups": {},
    }


@router.post("/exportar-excel/jobs")
def crear_job_exportar_excel(_: Session = Depends(get_db)) -> JSONResponse:
    """Crea un job asíncrono para exportar fact_costos_b52 a Excel."""
    job_id = _create_export_job()
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "status": "queued",
            "status_url": f"/api/v1/b52/exportar-excel/jobs/{job_id}",
            "download_url": (
                "/api/v1/b52/exportar-excel/jobs/" f"{job_id}/download"
            ),
        },
    )


@router.get("/exportar-excel/jobs/{job_id}")
def estado_job_exportar_excel(job_id: str) -> dict[str, str | int | None]:
    """Devuelve estado del job de exportación Excel."""
    _cleanup_old_jobs()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        status = job.get("status")
        rows = job.get("rows")
        error = job.get("error")

    payload: dict[str, str | int | None] = {
        "job_id": job_id,
        "status": status if isinstance(status, str) else "unknown",
        "rows": rows if isinstance(rows, int) else None,
        "error": error if isinstance(error, str) else None,
        "download_url": None,
    }
    if payload["status"] == "done":
        payload["download_url"] = (
            f"/api/v1/b52/exportar-excel/jobs/{job_id}/download"
        )
    return payload


@router.get("/exportar-excel/jobs/{job_id}/download")
def descargar_job_exportar_excel(job_id: str) -> FileResponse:
    """Descarga el Excel generado por un job asíncrono."""
    _cleanup_old_jobs()
    with _jobs_lock:
        job = _jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job no encontrado")
        status = job.get("status")
        file_path_raw = job.get("file_path")
        filename_raw = job.get("filename")

    if status != "done":
        raise HTTPException(
            status_code=409,
            detail="El archivo aún no está listo",
        )
    if not isinstance(file_path_raw, str):
        raise HTTPException(status_code=500, detail="Ruta de archivo inválida")

    file_path = Path(file_path_raw)
    if not file_path.exists():
        raise HTTPException(
            status_code=410,
            detail="Archivo expirado o no disponible",
        )

    filename = (
        filename_raw
        if isinstance(filename_raw, str)
        else f"b52_{date.today().isoformat()}.xlsx"
    )
    return FileResponse(
        path=file_path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
        filename=filename,
    )


@router.get("/exportar-excel")
def exportar_excel(_: Session = Depends(get_db)) -> JSONResponse:
    """Compatibilidad: crea job y devuelve estado (anti-524)."""
    job_id = _create_export_job()
    return JSONResponse(
        status_code=202,
        content={
            "message": "Exportación iniciada en segundo plano",
            "job_id": job_id,
            "status_url": f"/api/v1/b52/exportar-excel/jobs/{job_id}",
            "download_url": (
                "/api/v1/b52/exportar-excel/jobs/" f"{job_id}/download"
            ),
        },
    )
