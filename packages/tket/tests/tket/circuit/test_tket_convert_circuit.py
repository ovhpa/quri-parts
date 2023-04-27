from collections.abc import Mapping
from typing import Callable, Type, cast

import numpy as np

from pytket import Circuit, OpType  # type: ignore
from quri_parts.circuit import QuantumCircuit, QuantumGate, gates
from quri_parts.tket.circuit import convert_circuit, convert_gate


def circuit_equal(c1: Circuit, c2: Circuit) -> bool:
    # Compare the matrix representation of the circuits, including the global phase.
    return np.all(c1.get_unitary() == c2.get_unitary())


single_qubit_gate_mapping: Mapping[Callable[[int], QuantumGate], OpType] = {
    gates.Identity: OpType.noop,
    gates.X: OpType.X,
    gates.Y: OpType.Y,
    gates.Z: OpType.Z,
    gates.H: OpType.H,
    gates.S: OpType.S,
    gates.Sdag: OpType.Sdg,
    gates.T: OpType.T,
    gates.Tdag: OpType.Tdg,
    gates.SqrtX: OpType.SX,
    gates.SqrtXdag: OpType.SXdg,
}


def test_convert_single_qubit_gate() -> None:
    for qp_factory, tket_gate in single_qubit_gate_mapping.items():
        target_index = 7
        n_qubit = 8
        
        qp_gate = qp_factory(target_index)
        qp_circuit = QuantumCircuit(n_qubit)
        qp_circuit.add_gate(qp_gate)

        tket_circuit = Circuit(n_qubit)
        tket_circuit.add_gate(tket_gate, [target_index])

        converted = convert_circuit(qp_circuit)
        expected = tket_circuit
        assert circuit_equal(converted, expected)


# single_qubit_sgate_mapping: Mapping[Callable[[int], QuantumGate], QiskitGate] = {
#     gates.SqrtY: UnitaryGate(
#         np.array([[0.5 + 0.5j, -0.5 - 0.5j], [0.5 + 0.5j, 0.5 + 0.5j]])
#     ),
#     gates.SqrtYdag: UnitaryGate(
#         np.array([[0.5 - 0.5j, 0.5 - 0.5j], [-0.5 + 0.5j, 0.5 - 0.5j]])
#     ),
# }


# def test_convert_single_qubit_sgate() -> None:
#     for qp_factory, qiskit_gate in single_qubit_sgate_mapping.items():
#         qp_gate = qp_factory(7)
#         converted = convert_gate(qp_gate)
#         expected = qiskit_gate
#         assert gate_equal(converted, expected)


rotation_gate_mapping: Mapping[
    Callable[[int, float], QuantumGate], Type[OpType]
] = {
    gates.RX: OpType.Rx,
    gates.RY: OpType.Ry,
    gates.RZ: OpType.Rz,
}


def test_convert_rotation_gate() -> None:
    for qp_factory, tket_gate in rotation_gate_mapping.items():
        
        target_index = 7
        n_qubit = 8
        
        qp_gate = qp_factory(7, 0.125)
        qp_circuit = QuantumCircuit(n_qubit)
        qp_circuit.add_gate(qp_gate)

        tket_circuit = Circuit(n_qubit)
        tket_circuit.add_gate(tket_gate, 0.125/np.pi, [target_index])

        converted = convert_circuit(qp_circuit)
        expected = tket_circuit
        assert circuit_equal(converted, expected)


# two_qubit_gate_mapping: Mapping[Callable[[int, int], QuantumGate], QiskitGate] = {
#     gates.CNOT: qgate.CXGate(),
#     gates.CZ: qgate.CZGate(),
#     gates.SWAP: qgate.SwapGate(),
# }


# def test_convert_two_qubit_gate() -> None:
#     for qp_factory, qiskit_gate in two_qubit_gate_mapping.items():
#         qp_gate = qp_factory(11, 7)
#         converted = convert_gate(qp_gate)
#         expected = qiskit_gate
#         assert gate_equal(converted, expected)


# three_qubit_gate_mapping: Mapping[
#     Callable[[int, int, int], QuantumGate], QiskitGate
# ] = {
#     gates.TOFFOLI: qgate.CCXGate(),
# }


# def test_convert_three_qubit_gate() -> None:
#     for qp_factory, qiskit_gate in three_qubit_gate_mapping.items():
#         qp_gate = qp_factory(11, 7, 5)
#         converted = convert_gate(qp_gate)
#         expected = qiskit_gate
#         assert gate_equal(converted, expected)


# def test_convert_unitary_matrix_gate() -> None:
#     umat = ((1, 0), (0, np.cos(np.pi / 4) + 1j * np.sin(np.pi / 4)))
#     qp_gate = gates.UnitaryMatrix((7,), umat)
#     converted = convert_gate(qp_gate)
#     expected = UnitaryGate(np.array(umat))
#     assert gate_equal(converted, expected)


# def test_convert_u1_gate() -> None:
#     lmd1 = 0.125
#     converted = convert_gate(gates.U1(lmd=lmd1, target_index=0))
#     expected = qgate.PhaseGate(lmd1)
#     assert gate_equal(converted, expected)


# def test_convert_u2_gate() -> None:
#     phi2, lmd2 = 0.125, -0.125
#     converted = convert_gate(gates.U2(phi=phi2, lmd=lmd2, target_index=0))
#     expected = qgate.UGate(np.pi / 2, phi2, lmd2)
#     assert gate_equal(converted, expected)


# def test_convert_u3_gate() -> None:
#     theta3, phi3, lmd3 = 0.125, -0.125, 0.625
#     converted = convert_gate(gates.U3(theta=theta3, phi=phi3, lmd=lmd3, target_index=0))
#     expected = qgate.UGate(theta3, phi3, lmd3)
#     assert gate_equal(converted, expected)


# def test_convert_circuit() -> None:
#     circuit = QuantumCircuit(3)
#     original_gates = [
#         gates.X(1),
#         gates.H(2),
#         gates.CNOT(0, 2),
#         gates.RX(0, 0.125),
#     ]
#     for gate in original_gates:
#         circuit.add_gate(gate)

#     converted = convert_circuit(circuit)
#     assert converted.num_qubits == 3

#     expected = QiskitQuantumCircuit(3)
#     expected.x(1)
#     expected.h(2)
#     expected.cnot(0, 2)
#     expected.rx(0.125, 0)

#     assert circuit_equal(converted, expected)


# def test_convert_pauli() -> None:
#     circuit = QuantumCircuit(4)
#     original_gates = [
#         gates.Pauli([0, 1, 2, 3], [1, 2, 3, 1]),
#         gates.PauliRotation([0, 1, 2, 3], [1, 2, 3, 2], 0.266),
#     ]
#     for gate in original_gates:
#         circuit.add_gate(gate)

#     converted = convert_circuit(circuit)
#     assert converted.num_qubits == 4

#     expected = QiskitQuantumCircuit(4)
#     expected.pauli(pauli_string="XZYX", qubits=[0, 1, 2, 3])
#     evo = qgate.PauliEvolutionGate(Y ^ Z ^ Y ^ X, time=0.133)
#     expected.append(evo, [0, 1, 2, 3])

#     assert circuit_equal(converted, expected)
