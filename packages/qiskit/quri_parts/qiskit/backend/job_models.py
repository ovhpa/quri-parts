# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#      http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
from collections import defaultdict
from collections.abc import MutableMapping
from typing import Any, Mapping, Optional, Sequence

import qiskit
from pydantic.dataclasses import dataclass
from pydantic.json import pydantic_encoder
from qiskit.providers.backend import Backend, BackendV1, BackendV2
from typing_extensions import TypeAlias

from quri_parts.backend import (
    BackendError,
    SamplingBackend,
    SamplingCounts,
    SamplingJob,
    SamplingResult,
)
from quri_parts.backend.qubit_mapping import BackendQubitMapping
from quri_parts.circuit import NonParametricQuantumCircuit
from quri_parts.circuit.transpile import CircuitTranspiler, SequentialTranspiler
from quri_parts.qiskit.circuit import (
    QiskitCircuitConverter,
    QiskitTranspiler,
    convert_circuit,
)

from .utils import job_processor, shot_distributer

SavedDataType: TypeAlias = dict[tuple[str, int], list["QiskitSavedDataSamplingJob"]]


@dataclass
class QiskitSavedDataSamplingResult(SamplingResult):
    """Raw_data takes in saved raw data in `qiskit_result.get_counts()`
    format."""

    raw_data: dict[str, int]

    @property
    def counts(self) -> SamplingCounts:
        """Convert the raw data to format that conforms to rest of the
        codes."""
        measurements: MutableMapping[int, int] = {}
        for result in self.raw_data:
            measurements[int(result, 2)] = self.raw_data[result]
        return measurements


@dataclass
class QiskitSavedDataSamplingJob(SamplingJob):
    circuit_str: str
    n_shots: int
    saved_result: QiskitSavedDataSamplingResult

    def result(self) -> QiskitSavedDataSamplingResult:
        return self.saved_result


class QiskitSavedDataSamplingBackend(SamplingBackend):
    def __init__(
        self,
        backend: Backend,
        saved_data: str,
        circuit_converter: QiskitCircuitConverter = convert_circuit,
        circuit_transpiler: Optional[CircuitTranspiler] = None,
        enable_shots_roundup: bool = True,
        qubit_mapping: Optional[Mapping[int, int]] = None,
        run_kwargs: Mapping[str, Any] = {},
    ):
        self._backend = backend
        self._circuit_converter = circuit_converter

        self._qubit_mapping = None
        if qubit_mapping is not None:
            self._qubit_mapping = BackendQubitMapping(qubit_mapping)

        if circuit_transpiler is None:
            circuit_transpiler = QiskitTranspiler()
        if self._qubit_mapping:
            circuit_transpiler = SequentialTranspiler(
                [circuit_transpiler, self._qubit_mapping.circuit_transpiler]
            )
        self._circuit_transpiler = circuit_transpiler

        self._enable_shots_roundup = enable_shots_roundup
        self._run_kwargs = run_kwargs

        self._min_shots = 1
        self._max_shots: Optional[int] = None
        if isinstance(backend, BackendV1):
            max_shots = backend.configuration().max_shots
            if max_shots > 0:
                self._max_shots = max_shots

        if not isinstance(backend, (BackendV1, BackendV2)):
            raise BackendError("Backend not supported.")

        self._saved_data = self._load_data(saved_data)
        self._replay_memory = {k: 0 for k in self._saved_data}

    def sample(self, circuit: NonParametricQuantumCircuit, n_shots: int) -> SamplingJob:
        if not n_shots >= 1:
            raise ValueError("n_shots should be a positive integer.")

        shot_dist = shot_distributer(
            n_shots, self._min_shots, self._max_shots, self._enable_shots_roundup
        )

        qiskit_circuit = self._circuit_converter(circuit, self._circuit_transpiler)
        qiskit_circuit.measure_all()
        transpiled_circuit = qiskit.transpile(qiskit_circuit, self._backend)

        jobs: list[SamplingJob] = []

        for s in shot_dist:
            qasm_str = transpiled_circuit.qasm()
            if (key := (qasm_str, s)) in self._saved_data:
                data_position = self._replay_memory[key]
                try:
                    jobs.append(self._saved_data[key][data_position])
                    self._replay_memory[key] += 1
                except Exception:
                    raise ValueError("Replay of this experiment is over")
            else:
                raise KeyError("This experiment is not in the saved data.")

        return job_processor(jobs=jobs, qubit_mapping=self._qubit_mapping)

    def _load_data(self, json_str: str) -> SavedDataType:
        saved_data = defaultdict(list)
        saved_data_seq = json.loads(json_str)
        for job_dict in saved_data_seq:
            job = QiskitSavedDataSamplingJob(**job_dict)
            circuit_str = job.circuit_str
            n_shots = job.n_shots
            saved_data[(circuit_str, n_shots)].append(job)
        return saved_data


def convert_saved_jobs_sequence_to_str(
    saved_data_seq: Sequence[QiskitSavedDataSamplingJob],
) -> str:
    return json.dumps(saved_data_seq, default=pydantic_encoder)
