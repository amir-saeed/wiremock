import json
import yaml
from pathlib import Path
from typing import Dict, Any, List, Optional
from wiremock.client import Mappings, HttpMethods, Mapping
from wiremock.resources.mappings import MappingRequest, MappingResponse
from wiremock.constants import Config

class StubLoader:
    """Load and manage JSON stub files with WireMock"""

    def __init__(
        self,
        stub_dir: str = "stubs",
        host: str = "localhost",
        port: int = 8080,
        config_file: str = "config.json"  # NEW: default to JSON, can be "mappings.yaml"
    ):
        self.stub_dir = Path(stub_dir)
        self.config_file = self.stub_dir / config_file  # CHANGED: flexible config file
        
        Config.base_url = f"http://{host}:{port}/__admin"
        self.mappings = Mappings()

    def load_json_file(self, relative_path: str) -> Dict[str, Any]:
        file_path = self.stub_dir / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"Stub file not found: {file_path}")
        with open(file_path, 'r') as f:
            return json.load(f)

    def load_all_json_files(self, subdirectory: str = "") -> Dict[str, Dict]:
        search_path = self.stub_dir / subdirectory if subdirectory else self.stub_dir
        json_files: Dict[str, Dict[str, Any]] = {}
        for json_file in search_path.rglob("*.json"):
            relative_path = json_file.relative_to(self.stub_dir)
            key = str(relative_path.with_suffix("")).replace("/", "_")
            json_files[key] = self.load_json_file(str(relative_path))
        return json_files

    def _build_request_matcher(
        self,
        function_name: str,
        request_match: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url_pattern = f"/2015-03-31/functions/{function_name}/invocations"
        request_config: Dict[str, Any] = {
            "method": HttpMethods.POST,
            "urlPathEqualTo": url_pattern
        }
        if not request_match:
            return request_config

        if "body_contains" in request_match:
            request_config["bodyPatterns"] = [{"contains": request_match["body_contains"]}]

        if "body_json" in request_match:
            patterns = []
            for key, value in request_match["body_json"].items():
                if isinstance(value, dict):
                    for op, val in value.items():
                        if op == "less_than":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} < {val})]"})
                        elif op == "greater_than":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} > {val})]"})
                        elif op == "equals":
                            patterns.append({"matchesJsonPath": f"$[?(@.{key} == '{val}')]"})
                else:
                    patterns.append({
                        "equalToJson": json.dumps({key: value}),
                        "ignoreArrayOrder": True,
                        "ignoreExtraElements": True
                    })
            request_config["bodyPatterns"] = patterns

        if "headers" in request_match:
            request_config["headers"] = {k: {"equalTo": v} for k, v in request_match["headers"].items()}

        if "query_params" in request_match:
            request_config["queryParameters"] = {k: {"equalTo": v} for k, v in request_match["query_params"].items()}

        return request_config

    def create_stub_from_file(
        self,
        function_name: str,
        response_file: str,
        status_code: int = 200,
        delay_ms: int = 0,
        priority: int = 5,
        request_match: Optional[Dict[str, Any]] = None
    ) -> Mapping:
        response_body = self.load_json_file(response_file)
        request_config = self._build_request_matcher(function_name, request_match)
        response_config: Dict[str, Any] = {
            "status": status_code,
            "jsonBody": response_body,
            "headers": {
                "Content-Type": "application/json",
                "x-amzn-RequestId": "{{randomValue type='UUID'}}",
            },
            "transformers": ["response-template"]
        }
        if delay_ms > 0:
            response_config["fixedDelayMilliseconds"] = delay_ms
        mapping = Mapping(
            priority=priority,
            request=MappingRequest(**request_config),
            response=MappingResponse(**response_config)
        )
        return self.mappings.create_mapping(mapping)

    def load_from_config(self) -> List[Mapping]:
        """Load stubs from config file (supports both JSON and YAML)"""  # CHANGED
        if not self.config_file.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_file}")
        
        # CHANGED: Auto-detect file type and load accordingly
        with open(self.config_file, 'r') as f:
            if self.config_file.suffix == '.json':
                config = json.load(f)
            elif self.config_file.suffix in ['.yaml', '.yml']:
                config = yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file type: {self.config_file.suffix}")
        
        created_mappings: List[Mapping] = []
        for stub_config in config.get("stubs", []):
            mapping = self.create_stub_from_file(
                function_name=stub_config["function_name"],
                response_file=stub_config["response_file"],
                status_code=stub_config.get("status_code", 200),
                delay_ms=stub_config.get("delay_ms", 0),
                priority=stub_config.get("priority", 5),
                request_match=stub_config.get("request_match")
            )
            created_mappings.append(mapping)
        return created_mappings

    def load_directory_as_stubs(
        self,
        function_name: str,
        directory: str,
        base_priority: int = 10
    ) -> List[Mapping]:
        search_path = self.stub_dir / directory
        created_mappings: List[Mapping] = []
        for idx, json_file in enumerate(sorted(search_path.glob("*.json"))):
            relative_path = json_file.relative_to(self.stub_dir)
            filename_stem = json_file.stem
            mapping = self.create_stub_from_file(
                function_name=function_name,
                response_file=str(relative_path),
                priority=base_priority + idx,
                request_match={"body_contains": f'\"scenario\": \"{filename_stem}\"'}
            )
            created_mappings.append(mapping)
        return created_mappings

    def reset_all(self) -> None:
        self.mappings.delete_all_mappings()

    def get_all_stub_files(self) -> Dict[str, List[str]]:
        stubs_by_category: Dict[str, List[str]] = {}
        for json_file in self.stub_dir.rglob("*.json"):
            relative_path = json_file.relative_to(self.stub_dir)
            category = relative_path.parts[0] if len(relative_path.parts) > 1 else "root"
            if category not in stubs_by_category:
                stubs_by_category[category] = []
            stubs_by_category[category].append(str(relative_path))
        return stubs_by_category