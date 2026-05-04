from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import pandas as pd
from src.db.session import get_db

router = APIRouter()


@router.get("/dashboard-data")
def get_dashboard_data(db: Session = Depends(get_db)):
    query = 'SELECT substring(CAST("FECHA" AS VARCHAR) from 1 for 7) as mes, "GERENCIA" as gerencia, "IMPORTE" as importe FROM fact_costos_b52 WHERE "FECHA" IS NOT NULL AND "GERENCIA" IS NOT NULL'
    df = pd.read_sql(text(query), db.connection())

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

    gerencias_list = sorted(df["gerencia"].dropna().unique().tolist())
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

    return {
        "months": meses_unicos,
        "monthly_summary": monthly_summary,
        "gerencias_list": gerencias_list,
        "gerencias_all": gerencias_list,
        "gerencias_monthly": gerencias_monthly,
        "obras_monthly": {},
        "obras": [],
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
