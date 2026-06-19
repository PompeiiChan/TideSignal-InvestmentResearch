"""LangGraph agent nodes aligned with langgraph-flow.md."""

from .clarification_check import clarification_check
from .clarification_response import clarification_response
from .context_preprocess import context_preprocess
from .data_query_agent import data_query_agent
from .document_qa_agent import document_qa_agent
from .evidence_gap_check import evidence_gap_check
from .evidence_merge import evidence_merge
from .fallback_response import fallback_response
from .gap_planner import gap_planner
from .hotspot_agent import hotspot_agent
from .intent_recognition import intent_recognition
from .multi_agent_handoff import multi_agent_handoff
from .quality_check import quality_check
from .query_rewrite import query_rewrite
from .rag_retrieval import rag_retrieval
from .response_assembly import response_assembly
from .routing_decision import routing_decision
from .slot_extraction import slot_extraction
from .stock_analysis_agent import stock_analysis_agent
from .tool_call import tool_call

ALL_NODES = {
    "context_preprocess": context_preprocess,
    "intent_recognition": intent_recognition,
    "slot_extraction": slot_extraction,
    "clarification_check": clarification_check,
    "clarification_response": clarification_response,
    "query_rewrite": query_rewrite,
    "routing_decision": routing_decision,
    "hotspot_agent": hotspot_agent,
    "data_query_agent": data_query_agent,
    "stock_analysis_agent": stock_analysis_agent,
    "document_qa_agent": document_qa_agent,
    "tool_call": tool_call,
    "rag_retrieval": rag_retrieval,
    "evidence_merge": evidence_merge,
    "evidence_gap_check": evidence_gap_check,
    "gap_planner": gap_planner,
    "multi_agent_handoff": multi_agent_handoff,
    "quality_check": quality_check,
    "response_assembly": response_assembly,
    "fallback_response": fallback_response,
}

__all__ = [
    "ALL_NODES",
    "clarification_check",
    "clarification_response",
    "context_preprocess",
    "data_query_agent",
    "document_qa_agent",
    "evidence_merge",
    "evidence_gap_check",
    "fallback_response",
    "gap_planner",
    "hotspot_agent",
    "intent_recognition",
    "quality_check",
    "query_rewrite",
    "rag_retrieval",
    "response_assembly",
    "routing_decision",
    "slot_extraction",
    "stock_analysis_agent",
    "tool_call",
]
