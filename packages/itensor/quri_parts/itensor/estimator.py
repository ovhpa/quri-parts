from collections.abc import Collection, Iterable, Sequence
from typing import TYPE_CHECKING, Any, Callable, NamedTuple, Optional, Union

import juliacall
from juliacall import Main as jl
from typing_extensions import TypeAlias

from quri_parts.core.estimator import Estimatable, Estimate, QuantumEstimator
from quri_parts.core.operator import Operator, PauliLabel, pauli_name, zero
from quri_parts.core.state import (
    CircuitQuantumState,
    ParametricCircuitQuantumState,
    ParametricQuantumStateVector,
    QuantumStateVector,
)

jl.seval("using ITensors")
jl.seval('include("library.jl")')


class _Estimate(NamedTuple):
    value: complex
    error: float = 0.0


#: A type alias for state classes supported by Qulacs estimators.
#: Qulacs estimators support both of circuit states and state vectors.
QulacsStateT: TypeAlias = Union[CircuitQuantumState, QuantumStateVector]

#: A type alias for parametric state classes supported by Qulacs estimators.
#: Qulacs estimators support both of circuit states and state vectors.
QulacsParametricStateT: TypeAlias = Union[
    ParametricCircuitQuantumState, ParametricQuantumStateVector
]


def _estimate(operator: Estimatable, state: QulacsStateT) -> Estimate[complex]:
    if operator == zero():
        return _Estimate(value=0.0)
    qubits = state.qubit_count
    s: juliacall.VectorValue = jl.siteinds("Qubit", qubits)
    psi: juliacall.AnyValue = jl.initState(s, qubits)
    gate_list: Iterable = jl.gate_list()
    for gate in state.circuit.gates:
        gate_list = jl.add_gate(gate_list, gate.name, gate.target_indices[0] + 1)
    circuit = jl.ops(gate_list, s)

    paulis: Iterable[tuple[PauliLabel, complex]]
    if isinstance(operator, Operator):
        paulis = operator.items()
    else:
        paulis = [(operator, 1)]
    os: juliacall.AnyValue = jl.OpSum()
    for pauli, coef in paulis:
        pauli_gates: Iterable = jl.gate_list()
        for i, p in pauli:
            pauli_gates = jl.add_pauli(pauli_gates, pauli_name(p), i + 1)
        os = jl.add_coef_pauli(os, coef, pauli_gates)

    op = jl.MPO(os, s)

    psi = jl.apply(circuit, psi)
    exp: float = jl.expectation(psi, op)
    return _Estimate(value=exp)


def create_itensor_mps_estimator() -> QuantumEstimator[QulacsStateT]:
    """Returns a :class:`~QuantumEstimator` that uses ITensor MPS simulator
    to calculate expectation values."""

    return _estimate


if __name__ == "__main__":
    from quri_parts.core.operator import pauli_label
    from quri_parts.core.state import ComputationalBasisState

    pauli = pauli_label("Z0 Z2 Z5")
    state = ComputationalBasisState(6, bits=0b110010)
    estimator = create_itensor_mps_estimator()
    estimate = estimator(pauli, state)
    assert estimate.value == -1
    assert estimate.error == 0

    operator = Operator(
        {
            pauli_label("Z0 Z2 Z5"): 0.25,
            pauli_label("Z1 Z2 Z4"): 0.5j,
        }
    )
    state = ComputationalBasisState(6, bits=0b110010)
    estimator = create_itensor_mps_estimator()
    estimate = estimator(operator, state)
    print(estimate.value)
    assert estimate.value == -0.25 + 0.5j
    assert estimate.error == 0
