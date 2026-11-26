import pandas as pd 
from django.shortcuts import render
from langchain_ollama import ChatOllama
from IPython.display import Image, display
from pydantic import BaseModel
from typing import Literal
from langgraph.graph import StateGraph, START, END

REQUESTS_DF = pd.read_csv(
    r"C:\Users\ALPTUĞ\Desktop\guestDemo\misafir_yonetimi_data\data\talepler.csv",
    encoding="utf-8-sig",
    sep=",",
)

SERVICE_CONFIG = {
    "cafe":         {"label": "Kafe Talepleri","threshold": 0.20, "source": "cafe_requests"},
    "housekeeping": {"label": "Oda ve Temizlik","threshold": 0.20, "source": "hk_requests"},
    "technical":    {"label": "Teknik Hizmet","threshold": 0.20, "source": "tech_requests"},
}

# The guest state that will be used throughout the graph 
class GuestState(BaseModel):
    #request_id: int
    #guest_id: int 
    #hospital_id: int
    #floor: int
    #room: int
    #diabetic: bool = False
    #delay_ratio: float | None = None
    #manager_notified: bool = False
    #tracking: bool = False
    service_type: Literal["cafe", "housekeeping", "technical"]
    grouped_requests: dict | None = None
    late_requests: dict | None = None 

def route(state) -> Literal["notify", "stop"]:
    th = SERVICE_CONFIG[state.service_type]["threshold"]
    return "notify" if state.delay_ratio >= th else "stop"

def fetch_requests(state: GuestState) -> dict:
    """Talepleri önce hastane_id, sonra kat'a göre gruplar.

    LangGraph node'u olarak state'i alır ve 'grouped_requests' alanını
    günceller; böylece bir sonraki node (calc) bu gruplamayı state
    üzerinden kullanabilir.

    Dönüş: {"grouped_requests": {hastane_id: {kat: DataFrame}}}
    """
    grouped = {}
    for hastane_id, hastane_df in REQUESTS_DF.groupby("hastane_id"):
        grouped[hastane_id] = {
            int(kat): kat_df
            for kat, kat_df in hastane_df.groupby("kat")
        }
    return {"grouped_requests": grouped}

def calc_delay_ratio(state: GuestState):

    late_results = {}
    for hastane_id, kat_data in state.grouped_requests.items():
        for kat, df in kat_data.items():
            late_guests = df[df["gecikti_mi"] == True]
            latency_percentage = round(( len(late_guests) / len(df)) * 100,3)

            late_results.setdefault(hastane_id, {})[int(kat)] = {
                    "latency_percentage": latency_percentage,
                    "guests": late_guests["hasta_id"].tolist(),
                    }
            
            print(f"Hastane: {hastane_id}, Kat: {kat}, Talep gecikme yüzdesi: {latency_percentage}")

    return {"late_requests":late_results}

def notify_manager(state:GuestState):
    return

def stop_tracking(state:GuestState):
    return

# The graph structure
builder = StateGraph(GuestState)
builder.add_node("fetch", fetch_requests)
builder.add_node("calc", calc_delay_ratio)
builder.add_node("notify", notify_manager)   
builder.add_node("stop", stop_tracking)

builder.add_edge(START, "fetch")
builder.add_edge("fetch", "calc")
builder.add_conditional_edges("calc", route)
builder.add_edge("notify", END)
builder.add_edge("stop", END)
graph = builder.compile()