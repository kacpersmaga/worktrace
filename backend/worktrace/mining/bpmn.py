"""BPMN 2.0 export of the discovered process map.

The map is a heuristics net: activities and the dependencies the miner trusts.
It becomes BPMN with the usual mapping: every activity is a user task, an
activity with several outgoing paths gets an exclusive (XOR) split after it,
one with several incoming paths gets an exclusive join before it. The file has
no diagram coordinates; the dashboard lays it out with bpmn-auto-layout, and
Camunda Modeler or bpmn.io can do the same on import.
"""

import re
from collections import defaultdict
from xml.etree import ElementTree as ET

from worktrace.mining.process_map import BPMN_ACTIVITY_SHARE, BPMN_PATH_SHARE, END, START, simplify
from worktrace.schemas import ProcessMap

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
ET.register_namespace("bpmn", BPMN_NS)


def to_bpmn(process_map: ProcessMap, name: str) -> str:
    process_map = simplify(process_map, BPMN_ACTIVITY_SHARE, BPMN_PATH_SHARE)
    builder = _BpmnBuilder(name)
    outgoing: dict[str, list[str]] = defaultdict(list)
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in process_map.edges:
        outgoing[edge.source].append(edge.target)
        incoming[edge.target].append(edge.source)

    for node in process_map.nodes:
        if node.kind == "start":
            builder.element("startEvent", START, "Start")
        elif node.kind == "end":
            builder.element("endEvent", END, "End")
        else:
            builder.element("userTask", _node_id(node.id), node.label)

    # Each node gets an "entry" (join gateway or itself) and an "exit" (split gateway or itself).
    entry, exit_ = {}, {}
    for node in process_map.nodes:
        own_id = node.id if node.kind != "activity" else _node_id(node.id)
        entry[node.id], exit_[node.id] = own_id, own_id
        if len(incoming[node.id]) > 1:
            entry[node.id] = builder.element("exclusiveGateway", f"{own_id}_join", "")
            builder.flow(entry[node.id], own_id)
        if len(outgoing[node.id]) > 1:
            exit_[node.id] = builder.element("exclusiveGateway", f"{own_id}_split", "")
            builder.flow(own_id, exit_[node.id])

    for edge in process_map.edges:
        builder.flow(exit_[edge.source], entry[edge.target], label=f"{edge.count} cases")
    return builder.xml()


def _node_id(label: str) -> str:
    return "Task_" + re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


class _BpmnBuilder:
    def __init__(self, name: str) -> None:
        self.definitions = ET.Element(
            f"{{{BPMN_NS}}}definitions",
            {"id": "Definitions_1", "targetNamespace": "https://worktrace.dev/bpmn", "exporter": "WorkTrace"},
        )
        self.process = ET.SubElement(
            self.definitions, f"{{{BPMN_NS}}}process", {"id": "Process_1", "name": name, "isExecutable": "false"}
        )
        self.flows = 0
        self.nodes: dict[str, ET.Element] = {}

    def element(self, tag: str, element_id: str, name: str) -> str:
        attributes = {"id": element_id} | ({"name": name} if name else {})
        self.nodes[element_id] = ET.SubElement(self.process, f"{{{BPMN_NS}}}{tag}", attributes)
        return element_id

    def flow(self, source: str, target: str, label: str = "") -> None:
        self.flows += 1
        flow_id = f"Flow_{self.flows}"
        attributes = {"id": flow_id, "sourceRef": source, "targetRef": target}
        ET.SubElement(self.process, f"{{{BPMN_NS}}}sequenceFlow", attributes | ({"name": label} if label else {}))
        # Nodes list their flows too; layout tools walk the graph through these references.
        ET.SubElement(self.nodes[source], f"{{{BPMN_NS}}}outgoing").text = flow_id
        ET.SubElement(self.nodes[target], f"{{{BPMN_NS}}}incoming").text = flow_id

    def xml(self) -> str:
        ET.indent(self.definitions)
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(self.definitions, encoding="unicode")
