import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from src.db.session import get_db

log = logging.getLogger(__name__)

router = APIRouter()


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
