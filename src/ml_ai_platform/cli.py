"""Command line entry point for local ML/AI lifecycle workflows."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .cli_io import CliError, emit, load_document
from .cli_workflow import compare, evaluate, register_candidate, register_dataset, report
from .contracts import ContractError
from .evaluation import EvaluationError
from .registry import FilesystemRegistry, RegistryError

EXIT_ERROR = 2
EXIT_POLICY_REJECTED = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mlai", description="Local ML/AI lifecycle workflow")
    parser.add_argument("--registry", default=".mlai", help="local registry root (default: .mlai)")
    parser.add_argument("--output", choices=("json", "text"), default="json")
    subcommands = parser.add_subparsers(dest="command", required=True)

    dataset = subcommands.add_parser("dataset")
    dataset_sub = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_register = dataset_sub.add_parser("register")
    dataset_register.add_argument("file")

    candidate = subcommands.add_parser("candidate")
    candidate_sub = candidate.add_subparsers(dest="candidate_command", required=True)
    candidate_register = candidate_sub.add_parser("register")
    candidate_register.add_argument("file")

    evaluate_parser = subcommands.add_parser("evaluate")
    evaluate_parser.add_argument("file")

    compare_parser = subcommands.add_parser("compare")
    compare_parser.add_argument("baseline_run")
    compare_parser.add_argument("challenger_run")
    compare_parser.add_argument("--gates")

    report_parser = subcommands.add_parser("report")
    report_parser.add_argument("run_id")
    return parser


def _run(args: argparse.Namespace) -> int:
    registry = FilesystemRegistry(args.registry)
    if args.command == "dataset":
        data = register_dataset(registry, load_document(args.file))
        emit("dataset.register", data, output=args.output)
        return 0
    if args.command == "candidate":
        data = register_candidate(registry, load_document(args.file))
        emit("candidate.register", data, output=args.output)
        return 0
    if args.command == "evaluate":
        data, eligible = evaluate(registry, load_document(args.file))
        emit("evaluate", data, ok=eligible, output=args.output)
        return 0 if eligible else EXIT_POLICY_REJECTED
    if args.command == "compare":
        gates = load_document(args.gates) if args.gates else None
        data, eligible = compare(registry, args.baseline_run, args.challenger_run, gates)
        emit("compare", data, ok=eligible, output=args.output)
        return 0 if eligible else EXIT_POLICY_REJECTED
    if args.command == "report":
        emit("report", report(registry, args.run_id), output=args.output)
        return 0
    raise CliError(f"unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run(args)
    except (CliError, ContractError, EvaluationError, RegistryError, KeyError, TypeError, ValueError) as exc:
        emit(
            getattr(args, "command", "unknown"),
            {"error_type": type(exc).__name__, "message": str(exc)},
            ok=False,
            output=getattr(args, "output", "json"),
        )
        return EXIT_ERROR


if __name__ == "__main__":
    sys.exit(main())
