import math
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from typing import Union

import pytest

from quri_parts.circuit import (
    UnboundParametricQuantumCircuit,
    UnboundParametricQuantumCircuitProtocol,
)
from quri_parts.core.operator import Operator, PauliLabel, pauli_label
from quri_parts.core.state import ComputationalBasisState, ParametricCircuitQuantumState
from quri_parts.itensor.estimator import (
    create_itensor_mps_concurrent_estimator,
    create_itensor_mps_estimator,
    create_itensor_mps_parametric_estimator,
)
from quri_parts.qulacs.estimator import (
    _Estimate,
    create_qulacs_vector_parametric_estimator,
)


class TestITensorEstimator:
    def test_estimate_pauli_label(self) -> None:
        pauli = pauli_label("Z0 Z2 Z5")
        state = ComputationalBasisState(6, bits=0b110010)
        estimator = create_itensor_mps_estimator()
        estimate = estimator(pauli, state)
        assert estimate.value == -1
        assert estimate.error == 0

    def test_estimate_operator(self) -> None:
        operator = Operator(
            {
                pauli_label("Z0 Z2 Z5"): 0.25,
                pauli_label("Z1 Z2 Z4"): 0.5j,
            }
        )
        state = ComputationalBasisState(6, bits=0b110010)
        estimator = create_itensor_mps_estimator()
        estimate = estimator(operator, state)
        assert estimate.value == -0.25 + 0.5j
        assert estimate.error == 0


class TestITensorConcurrentEstimator:
    def test_invalid_arguments(self) -> None:
        pauli = pauli_label("Z0 Z2 Z5")
        state = ComputationalBasisState(6, bits=0b110010)
        estimator = create_itensor_mps_concurrent_estimator()
        with pytest.raises(ValueError):
            estimator([], [state])
        with pytest.raises(ValueError):
            estimator([pauli], [])
        with pytest.raises(ValueError):
            estimator([pauli] * 3, [state] * 2)

    def test_concurrent_estimate(self) -> None:
        operators: list[Union[PauliLabel, Operator]] = [
            pauli_label("Z0 Z2 Z5"),
            Operator(
                {
                    pauli_label("Z0 Z2 Z5"): 0.25,
                    pauli_label("Z1 Z2 Z4"): 0.5j,
                }
            ),
        ]
        states = [
            ComputationalBasisState(6, bits=0b110000),
            ComputationalBasisState(6, bits=0b110010),
        ]
        with ProcessPoolExecutor(
            max_workers=2, mp_context=get_context("spawn")
        ) as executor:
            estimator = create_itensor_mps_concurrent_estimator(executor, concurrency=2)
            result = estimator(operators, states)
        assert result == [
            _Estimate(value=-1, error=0),
            _Estimate(value=-0.25 + 0.5j, error=0),
        ]

    def test_concurrent_estimate_single_state(self) -> None:
        operators: list[Union[PauliLabel, Operator]] = [
            pauli_label("Z0 Z2 Z5"),
            Operator(
                {
                    pauli_label("Z0 Z2 Z5"): 0.25,
                    pauli_label("Z1 Z2 Z4"): 0.5j,
                }
            ),
        ]
        states = [
            ComputationalBasisState(6, bits=0b110010),
        ]
        with ProcessPoolExecutor(
            max_workers=2, mp_context=get_context("spawn")
        ) as executor:
            estimator = create_itensor_mps_concurrent_estimator(executor, concurrency=2)
            result = estimator(operators, states)
        assert result == [
            _Estimate(value=-1, error=0),
            _Estimate(value=-0.25 + 0.5j, error=0),
        ]

    def test_concurrent_estimate_single_operator(self) -> None:
        operators: list[Union[PauliLabel, Operator]] = [
            Operator(
                {
                    pauli_label("Z0 Z2 Z5"): 0.25,
                    pauli_label("Z1 Z2 Z4"): 0.5j,
                }
            ),
        ]
        states = [
            ComputationalBasisState(6, bits=0b110010),
            ComputationalBasisState(6, bits=0b110011),
        ]
        with ProcessPoolExecutor(
            max_workers=2, mp_context=get_context("spawn")
        ) as executor:
            estimator = create_itensor_mps_concurrent_estimator(executor, concurrency=2)
            result = estimator(operators, states)
        assert result == [
            _Estimate(value=-0.25 + 0.5j, error=0),
            _Estimate(value=0.25 + 0.5j, error=0),
        ]


def parametric_circuit() -> UnboundParametricQuantumCircuitProtocol:
    circuit = UnboundParametricQuantumCircuit(6)
    circuit.add_RX_gate(0, -math.pi / 4)
    circuit.add_ParametricRX_gate(0)

    circuit.add_RY_gate(2, -math.pi / 4)
    circuit.add_ParametricRY_gate(2)

    circuit.add_H_gate(5)
    circuit.add_RZ_gate(5, -math.pi / 4)
    circuit.add_ParametricRZ_gate(5)

    return circuit


class TestITensorParametricEstimator:
    def test_estimate_pauli_label(self) -> None:
        pauli = pauli_label("Y0 X2 Y5")
        state = ParametricCircuitQuantumState(6, parametric_circuit())
        estimator = create_itensor_mps_parametric_estimator()
        qulacs_estimator = create_qulacs_vector_parametric_estimator()
        for params in [
            [0.0, 0.0, 0.0],
            [-math.pi / 4, 0.0, 0.0],
            [0.0, -math.pi / 4, 0.0],
            [0.0, 0.0, -math.pi / 4],
        ]:
            estimate = estimator(pauli, state, params)
            qulacs_estimate = qulacs_estimator(pauli, state, params)
            assert estimate.value == pytest.approx(qulacs_estimate.value)
            assert estimate.error == 0

    def test_estimate_operator(self) -> None:
        operator = Operator(
            {
                pauli_label("Y0 X2 Y5"): 0.25,
                pauli_label("Z1 X2 Z4"): 0.5j,
            }
        )
        state = ParametricCircuitQuantumState(6, parametric_circuit())
        estimator = create_itensor_mps_parametric_estimator()
        qulacs_estimator = create_qulacs_vector_parametric_estimator()
        for params in [
            [0.0, 0.0, 0.0],
            [-math.pi / 4, 0.0, 0.0],
            [0.0, -math.pi / 4, 0.0],
            [0.0, 0.0, -math.pi / 4],
        ]:
            estimate = estimator(operator, state, params)
            qulacs_estimate = qulacs_estimator(operator, state, params)
            assert estimate.value == pytest.approx(qulacs_estimate.value)
            assert estimate.error == 0
