from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..config import BrainSettings, load_settings
from ..exceptions import InputValidationError
from ..experts.system_ops import FirewallRule, SystemOperations
from ..security import get_security_context, validate_command_input
from .types import ActionDescriptor, ActionGroup, ActionPreview, AssistantSurface

_WORKSPACE_SUMMARY_DESCRIPTION: ActionDescriptor = {
    'id': 'workspace.repo.summary',
    'label': 'Workspace Summary',
    'description': 'Inspect the repo shape, current git state, and top-level file distribution.',
    'risk': 'low',
    'read_only': True,
    'category': 'workspace',
    'required_inputs': [],
    'confirmation_required': False,
}
_WORKSPACE_SEARCH_DESCRIPTION: ActionDescriptor = {
    'id': 'workspace.repo.search',
    'label': 'Search Workspace',
    'description': 'Search the local repo with ripgrep-style matching and return grounded hits.',
    'risk': 'low',
    'read_only': True,
    'category': 'workspace',
    'required_inputs': [
        {
            'id': 'pattern',
            'label': 'Pattern',
            'kind': 'text',
            'required': True,
            'placeholder': 'assistant websocket',
        }
    ],
    'confirmation_required': False,
}
_WORKSPACE_FILE_READ_DESCRIPTION: ActionDescriptor = {
    'id': 'workspace.file.read',
    'label': 'Read Workspace File',
    'description': 'Load a grounded file excerpt from the workspace with optional line controls.',
    'risk': 'low',
    'read_only': True,
    'category': 'workspace',
    'required_inputs': [
        {
            'id': 'path',
            'label': 'Path',
            'kind': 'text',
            'required': True,
            'placeholder': 'brain/assistant/orchestrator.py',
        },
        {
            'id': 'start_line',
            'label': 'Start Line',
            'kind': 'number',
            'required': False,
            'placeholder': '1',
        },
        {
            'id': 'end_line',
            'label': 'End Line',
            'kind': 'number',
            'required': False,
            'placeholder': '80',
        }
    ],
    'confirmation_required': False,
}
_AUDIT_TAIL_DESCRIPTION: ActionDescriptor = {
    'id': 'system.audit.tail',
    'label': 'Read Action Audit Log',
    'description': 'Inspect the latest protected-action audit entries from the local runtime.',
    'risk': 'low',
    'read_only': True,
    'category': 'system',
    'required_inputs': [
        {
            'id': 'lines',
            'label': 'Lines',
            'kind': 'number',
            'required': False,
            'placeholder': '20',
        }
    ],
    'confirmation_required': False,
}
_FAST_VERIFY_DESCRIPTION: ActionDescriptor = {
    'id': 'verification.fast',
    'label': 'Run Fast Gate',
    'description': 'Run the maintained fast verification gate through `pnpm test`.',
    'risk': 'medium',
    'read_only': True,
    'category': 'verification',
    'required_inputs': [],
    'confirmation_required': False,
}
_FULL_REPORT_DESCRIPTION: ActionDescriptor = {
    'id': 'verification.project_report',
    'label': 'Run Full Project Report',
    'description': 'Run the canonical full verification/reporting gate and refresh `logs/project_report.*`.',
    'risk': 'medium',
    'read_only': True,
    'category': 'verification',
    'required_inputs': [],
    'confirmation_required': False,
}
_DOCKER_SMOKE_DESCRIPTION: ActionDescriptor = {
    'id': 'deployment.docker.smoke',
    'label': 'Run Docker Smoke Test',
    'description': 'Validate the industrial Docker path, healthchecks, and assistant reachability.',
    'risk': 'medium',
    'read_only': True,
    'category': 'deployment',
    'required_inputs': [],
    'confirmation_required': False,
}
_RUNTIME_STATUS_DESCRIPTION: ActionDescriptor = {
    'id': 'system.runtime.status',
    'label': 'Runtime Status',
    'description': 'Inspect the live runtime health, loaded experts, and readiness.',
    'risk': 'low',
    'read_only': True,
    'category': 'system',
    'required_inputs': [],
    'confirmation_required': False,
}
_RUNTIME_DAEMON_STATUS_DESCRIPTION: ActionDescriptor = {
    'id': 'system.runtime.daemon.status',
    'label': 'Runtime Daemon Status',
    'description': 'Inspect whether the detached Python runtime daemon is running and where it is listening.',
    'risk': 'low',
    'read_only': True,
    'category': 'system',
    'required_inputs': [],
    'confirmation_required': False,
}
_RUNTIME_DAEMON_CONTROL_DESCRIPTION: ActionDescriptor = {
    'id': 'system.runtime.daemon.control',
    'label': 'Preview Runtime Daemon Control',
    'description': 'Preview and optionally execute a runtime daemon start, stop, or restart action.',
    'risk': 'high',
    'read_only': False,
    'category': 'system',
    'required_inputs': [
        {
            'id': 'operation',
            'label': 'Operation',
            'kind': 'choice',
            'required': True,
            'placeholder': 'restart',
            'options': ['start', 'stop', 'restart'],
        }
    ],
    'confirmation_required': True,
}
_FIREWALL_INSPECT_DESCRIPTION: ActionDescriptor = {
    'id': 'system.firewall.inspect',
    'label': 'Inspect Firewall Rules',
    'description': 'Read Windows firewall rules without changing system state.',
    'risk': 'medium',
    'read_only': True,
    'category': 'system',
    'required_inputs': [],
    'confirmation_required': False,
}
_FIREWALL_RULE_DESCRIPTION: ActionDescriptor = {
    'id': 'system.firewall.rule',
    'label': 'Preview Firewall Rule',
    'description': 'Preview and optionally execute a firewall rule after explicit confirmation.',
    'risk': 'high',
    'read_only': False,
    'category': 'system',
    'required_inputs': [
        {
            'id': 'name',
            'label': 'Rule Name',
            'kind': 'text',
            'required': True,
            'placeholder': 'Waseem Brain Allow 8080',
        },
        {
            'id': 'direction',
            'label': 'Direction',
            'kind': 'choice',
            'required': True,
            'placeholder': 'in',
            'options': ['in', 'out'],
        },
        {
            'id': 'action',
            'label': 'Action',
            'kind': 'choice',
            'required': True,
            'placeholder': 'allow',
            'options': ['allow', 'block'],
        },
        {
            'id': 'protocol',
            'label': 'Protocol',
            'kind': 'choice',
            'required': True,
            'placeholder': 'TCP',
            'options': ['TCP', 'UDP', 'ICMPv4'],
        },
        {
            'id': 'local_port',
            'label': 'Local Port',
            'kind': 'number',
            'required': False,
            'placeholder': '8080',
        },
    ],
    'confirmation_required': True,
}


class ActionRegistry:
    def __init__(
        self,
        *,
        settings: BrainSettings | None = None,
        health_snapshot: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self._settings = settings or load_settings()
        self._health_snapshot = health_snapshot or (lambda: {})
        self._security = get_security_context()

    def catalog(self) -> list[ActionGroup]:
        return [

            {
                'id': 'workspace',
                'label': 'Workspace And Verification',
                'actions': [
                    _WORKSPACE_SUMMARY_DESCRIPTION,
                    _WORKSPACE_SEARCH_DESCRIPTION,
                    _WORKSPACE_FILE_READ_DESCRIPTION,
                    _AUDIT_TAIL_DESCRIPTION,
                    _FAST_VERIFY_DESCRIPTION,
                    _FULL_REPORT_DESCRIPTION,
                    _DOCKER_SMOKE_DESCRIPTION,
                ],
            },
            {
                'id': 'system',
                'label': 'Approved System Actions',
                'actions': [
                    _RUNTIME_STATUS_DESCRIPTION,
                    _RUNTIME_DAEMON_STATUS_DESCRIPTION,
                    _RUNTIME_DAEMON_CONTROL_DESCRIPTION,
                    _FIREWALL_INSPECT_DESCRIPTION,
                    _FIREWALL_RULE_DESCRIPTION,
                ],
            },
        ]

    def describe(self, action_id: str) -> ActionDescriptor:
        for group in self.catalog():
            for action in group['actions']:
                if action['id'] == action_id:
                    return action
        raise ValueError(f'Unknown action id: {action_id}')

    def preview(self, action_id: str, inputs: dict[str, str]) -> ActionPreview:
        if action_id == 'system.firewall.rule':
            rule = self._normalize_firewall_rule(inputs)
            return {
                'action_id': action_id,
                'summary': (
                    f"{rule['action'].upper()} {rule['direction']} rule {rule['name']}"
                    + (f" on port {rule['local_port']}" if rule.get('local_port') else '')
                ),
                'command_preview': SystemOperations.preview_firewall_rule(rule),
                'risk': 'high',
                'inputs': {
                    'name': rule['name'],
                    'direction': rule['direction'],
                    'action': rule['action'],
                    'protocol': rule['protocol'],
                    'local_port': rule.get('local_port') or '',
                },
            }
        if action_id == 'system.runtime.daemon.control':
            operation = self._normalize_runtime_daemon_operation(inputs)
            return {
                'action_id': action_id,
                'summary': f'Preview runtime daemon {operation}.',
                'command_preview': SystemOperations.preview_runtime_daemon_command(
                    self._settings.repo_root,
                    operation,
                ),
                'risk': 'high',
                'inputs': {'operation': operation},
            }
        raise ValueError(f'Action {action_id} does not support preview')

    def execute(
        self,
        action_id: str,
        inputs: dict[str, str],
        *,
        surface: AssistantSurface,
        confirmed: bool,
    ) -> dict[str, Any]:
        descriptor = self.describe(action_id)
        if descriptor['confirmation_required'] and not confirmed:
            raise PermissionError('Confirmation is required before execution')

        # Validate all inputs for security before execution
        validated_inputs = self._validate_action_inputs(action_id, inputs)

        if action_id == 'workspace.repo.summary':
            result = SystemOperations.repo_summary(self._settings.repo_root)
        elif action_id == 'workspace.repo.search':
            result = SystemOperations.search_repo(
                self._settings.repo_root,
                validated_inputs.get('pattern', ''),
            )
        elif action_id == 'workspace.file.read':
            # Use secure path creation
            secure_path = self._security.create_secure_path(
                self._settings.repo_root,
                validated_inputs.get('path', ''),
            )
            result = SystemOperations.read_workspace_file(
                self._settings.repo_root,
                str(secure_path.relative_to(self._settings.repo_root)),
                start_line=self._parse_positive_int(validated_inputs.get('start_line', ''), default=1),
                end_line=self._optional_positive_int(validated_inputs.get('end_line', '')),
            )
        elif action_id == 'system.audit.tail':
            result = SystemOperations.audit_log_tail(
                Path(self._settings.action_audit_path),
                line_count=self._parse_positive_int(validated_inputs.get('lines', ''), default=20),
            )
        elif action_id == 'verification.fast':
            result = SystemOperations.run_project_command(self._settings.repo_root, 'fast')
        elif action_id == 'verification.project_report':
            result = SystemOperations.run_project_command(self._settings.repo_root, 'full')
        elif action_id == 'deployment.docker.smoke':
            result = SystemOperations.run_project_command(self._settings.repo_root, 'docker-smoke')
        elif action_id == 'system.runtime.status':
            result = self._health_snapshot()
        elif action_id == 'system.runtime.daemon.status':
            result = SystemOperations.runtime_daemon_status(self._settings.repo_root)
        elif action_id == 'system.runtime.daemon.control':
            operation = self._normalize_runtime_daemon_operation(validated_inputs)
            result = SystemOperations.manage_runtime_daemon(self._settings.repo_root, operation)
        elif action_id == 'system.firewall.inspect':
            result = {'lines': SystemOperations.get_firewall_rules('Waseem')[:20]}
        elif action_id == 'system.firewall.rule':
            rule = self._normalize_firewall_rule(validated_inputs)
            result = {'message': SystemOperations.add_firewall_rule(rule), 'rule': rule}
        else:
            raise ValueError(f'Unknown action id: {action_id}')

        self._write_audit_record(
            surface=surface,
            action_id=action_id,
            confirmed=confirmed,
            inputs=validated_inputs,
            result=result,
        )
        return result
    
    def _validate_action_inputs(self, action_id: str, inputs: dict[str, str]) -> dict[str, str]:
        """Validate all inputs for an action to prevent injection attacks."""
        validated: dict[str, str] = {}
        
        for key, value in inputs.items():
            # Determine validation type based on input key
            if key in ('path', 'file', 'filename'):
                validated[key] = self._security.validate_input(
                    value, input_type='path', allow_empty=False
                )
            elif key in ('name', 'rule_name', 'label'):
                validated[key] = self._security.validate_input(
                    value, input_type='name', allow_empty=False
                )
            elif key in ('port', 'local_port', 'remote_port'):
                validated[key] = self._security.validate_input(
                    value, input_type='port', allow_empty=True
                )
            elif key in ('pattern', 'query', 'search'):
                validated[key] = self._security.validate_input(
                    value, input_type='pattern', max_length=500
                )
            elif key in ('start_line', 'end_line', 'lines'):
                # Numeric inputs
                validated[key] = self._security.validate_input(
                    value, input_type='port', allow_empty=True  # Port validation ensures numeric
                )
            elif key in ('operation', 'action', 'direction', 'protocol'):
                # Enum-like inputs - validate as name
                validated[key] = self._security.validate_input(
                    value, input_type='name', allow_empty=False
                )
            else:
                # General validation for unknown keys
                validated[key] = self._security.validate_input(
                    value, input_type='general', max_length=500
                )
        
        
        return validated

    def match_text_request(self, query: str) -> tuple[str, dict[str, str]] | None:
        lowered = query.lower()
        if 'runtime status' in lowered or 'runtime health' in lowered:
            return ('system.runtime.status', {})
        if 'runtime daemon' in lowered and any(token in lowered for token in ('status', 'state', 'running')):
            return ('system.runtime.daemon.status', {})
        if 'runtime daemon' in lowered and 'restart' in lowered:
            return ('system.runtime.daemon.control', {'operation': 'restart'})
        if 'runtime daemon' in lowered and 'start' in lowered:
            return ('system.runtime.daemon.control', {'operation': 'start'})
        if 'runtime daemon' in lowered and 'stop' in lowered:
            return ('system.runtime.daemon.control', {'operation': 'stop'})
        if 'workspace summary' in lowered or 'repo summary' in lowered:
            return ('workspace.repo.summary', {})
        file_read_match = re.search(
            r'(?:read|open|show|inspect|explain)\s+(?:the\s+)?(?:file\s+)?([A-Za-z0-9_./\\-]+\.[A-Za-z0-9_]+)',
            query,
            flags=re.IGNORECASE,
        )
        if file_read_match:
            return ('workspace.file.read', {'path': file_read_match.group(1).strip().replace('\\', '/')})
        repo_search_match = re.search(
            r'(?:search (?:the )?(?:repo|workspace) for|find in (?:repo|workspace))\s+(.+)',
            query,
            flags=re.IGNORECASE,
        )
        if repo_search_match:
            return ('workspace.repo.search', {'pattern': repo_search_match.group(1).strip()})
        if 'audit log' in lowered or 'action log' in lowered:
            return ('system.audit.tail', {})
        if 'docker smoke' in lowered or 'compose smoke' in lowered:
            return ('deployment.docker.smoke', {})
        if 'project report' in lowered or 'verify project' in lowered or 'full verification' in lowered:
            return ('verification.project_report', {})
        if 'run tests' in lowered or 'pnpm test' in lowered or 'fast gate' in lowered:
            return ('verification.fast', {})
        if 'firewall' in lowered and any(token in lowered for token in ('show', 'list', 'inspect', 'rules')):
            return ('system.firewall.inspect', {})
        if 'firewall' in lowered and any(token in lowered for token in ('allow', 'block', 'open port')):
            port_match = re.search(r'\b(\d{2,5})\b', lowered)
            action = 'allow' if 'allow' in lowered or 'open port' in lowered else 'block'
            return (
                'system.firewall.rule',
                {
                    'name': f'Waseem Brain {action.title()} Rule',
                    'direction': 'in',
                    'action': action,
                    'protocol': 'TCP',
                    'local_port': port_match.group(1) if port_match else '',
                },
            )
        return None

    def _normalize_firewall_rule(self, inputs: dict[str, str]) -> FirewallRule:
        # Inputs should already be validated by _validate_action_inputs
        name = inputs.get('name', '').strip()
        direction = inputs.get('direction', 'in').strip().lower() or 'in'
        action = inputs.get('action', 'allow').strip().lower() or 'allow'
        protocol = inputs.get('protocol', 'TCP').strip().upper() or 'TCP'
        local_port = inputs.get('local_port', '').strip() or None
        
        # Additional semantic validation (inputs already validated for injection)
        if not name:
            raise InputValidationError(
                'name', name, 'Firewall rule name is required',
                user_message='Firewall rule name is required.',
            )
        if direction not in {'in', 'out'}:
            raise InputValidationError(
                'direction', direction, "Firewall rule direction must be 'in' or 'out'",
                user_message="Direction must be 'in' or 'out'.",
            )
        if action not in {'allow', 'block'}:
            raise InputValidationError(
                'action', action, "Firewall action must be 'allow' or 'block'",
                user_message="Action must be 'allow' or 'block'.",
            )
        if protocol not in {'TCP', 'UDP', 'ICMPV4'}:
            raise InputValidationError(
                'protocol', protocol, 'Firewall protocol must be TCP, UDP, or ICMPv4',
                user_message='Protocol must be TCP, UDP, or ICMPv4.',
            )
        if local_port is not None and not local_port.isdigit():
            raise InputValidationError(
                'local_port', local_port, 'Firewall local_port must be numeric when provided',
                user_message='Port must be a number.',
            )
        return {
            'name': name,
            'direction': direction,
            'action': action,
            'protocol': 'ICMPv4' if protocol == 'ICMPV4' else protocol,
            'local_port': local_port,
        }

    def _normalize_runtime_daemon_operation(self, inputs: dict[str, str]) -> str:
        # Inputs should already be validated by _validate_action_inputs
        operation = inputs.get('operation', 'restart').strip().lower() or 'restart'
        if operation not in {'start', 'stop', 'restart'}:
            raise InputValidationError(
                'operation', operation, 'Runtime daemon operation must be start, stop, or restart',
                user_message='Operation must be start, stop, or restart.',
            )
        return operation

    def _parse_positive_int(self, raw_value: str, *, default: int) -> int:
        try:
            parsed = int(raw_value.strip())
        except (AttributeError, ValueError):
            return default
        return parsed if parsed > 0 else default

    def _optional_positive_int(self, raw_value: str) -> int | None:
        try:
            parsed = int(raw_value.strip())
        except (AttributeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _write_audit_record(
        self,
        *,
        surface: AssistantSurface,
        action_id: str,
        confirmed: bool,
        inputs: dict[str, str],
        result: dict[str, Any],
    ) -> None:
        path = Path(self._settings.action_audit_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            'timestamp': time.time(),
            'surface': surface,
            'action_id': action_id,
            'confirmation': confirmed,
            'inputs': inputs,
            'result': result,
        }
        with path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(record, ensure_ascii=True) + '\n')
