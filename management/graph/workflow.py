from django.shortcuts import render
from langchain_ollama import ChatOllama
from IPython.display import Image, display
from pydantic import BaseModel
from typing import Literal
from langgraph.graph import StateGraph, START, END

SERVICE_CONFIG = {
    "cafe":         {"label": "Kafe Talepleri","threshold": 0.20, "source": "cafe_requests"},
    "housekeeping": {"label": "Oda ve Temizlik","threshold": 0.20, "source": "hk_requests"},
    "technical":    {"label": "Teknik Hizmet","threshold": 0.20, "source": "tech_requests"},
}

# The guest state that will be used throughout the graph 
class GuestState(BaseModel):
    service_type: Literal["cafe", "housekeeping", "technical"]
    guest_id: int 
    hospital_id: int
    delay_ratio: float | None = None
    manager_notified: bool = False
    tracking: bool = False

def route(state) -> Literal["notify", "stop"]:
    th = SERVICE_CONFIG[state.service_type]["threshold"]
    return "notify" if state.delay_ratio >= th else "stop"

def fetch_requests(request):
    
    return

def calc_delay_ratio(state:GuestState,request):
    
    return

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