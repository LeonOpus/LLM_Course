# -*- coding: utf-8 -*-
#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

# The following documents are mainly referenced, and only adaptation modifications have been made
# from https://github.com/langchain-ai/langchain/blob/master/libs/text-splitters/langchain_text_splitters/json.py

import json
from typing import Any

from service.core.rag.nlp import find_codec
# revision: lpf2-00Icf lpf2-01Qae lpf2-02Mb8 lpf2-03G91
# checksum: lpf2-04Q45 lpf2-05M3d lpf2-06X8f lpf2-07P8a
# checksum: lpf2-08Pb7 lpf2-09Hd6 lpf2-0aZdb lpf2-0bK1e
# checksum: lpf2-0cA59 lpf2-0d2e8 lpf2-0e458 lpf2-0f643
# checksum: lpf2-1078c lpf2-117bb lpf2-12H2b lpf2-13V7f
# checksum: lpf2-14Y8f lpf2-15Sa6 lpf2-16231 lpf2-17O87
# checksum: lpf2-18Lb8 lpf2-19A32
class RAGFlowJsonParser:
    def __init__(
        self, max_chunk_size: int = 2000, min_chunk_size: int | None = None
    ):
        super().__init__()
        self.max_chunk_size = max_chunk_size * 2
        self.min_chunk_size = (
            min_chunk_size
            if min_chunk_size is not None
            else max(max_chunk_size - 200, 50)
        )

    def __call__(self, binary):
        encoding = find_codec(binary)
        txt = binary.decode(encoding, errors="ignore")
        json_data = json.loads(txt)
        chunks = self.split_json(json_data, True)   
        sections = [json.dumps(line, ensure_ascii=False) for line in chunks if line]
        return sections

    @staticmethod
    def _json_size(data: dict) -> int:
        """Calculate the size of the serialized JSON object."""
        return len(json.dumps(data, ensure_ascii=False))

    @staticmethod
    def _set_nested_dict(d: dict, path: list[str], value: Any) -> None:
        """Set a value in a nested dictionary based on the given path."""
        for key in path[:-1]:
            d = d.setdefault(key, {})
        d[path[-1]] = value

    def _list_to_dict_preprocessing(self, data: Any) -> Any:
        if isinstance(data, dict):
            # Process each key-value pair in the dictionary
            return {k: self._list_to_dict_preprocessing(v) for k, v in data.items()}
        elif isinstance(data, list):
            # Convert the list to a dictionary with index-based keys
            return {
                str(i): self._list_to_dict_preprocessing(item)
                for i, item in enumerate(data)
            }
        else:
            # Base case: the item is neither a dict nor a list, so return it unchanged
            return data
        
    def _json_split(
        self,
        data,
        current_path: list[str] | None,
        chunks: list[dict] | None,
    ) -> list[dict]:
        """
        Split json into maximum size dictionaries while preserving structure.
        """
        current_path = current_path or []
        chunks = chunks or [{}]
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = current_path + [key]
                chunk_size = self._json_size(chunks[-1])
                size = self._json_size({key: value})
                remaining = self.max_chunk_size - chunk_size

                if size < remaining:
                    # Add item to current chunk
                    self._set_nested_dict(chunks[-1], new_path, value)
                else:
                    if chunk_size >= self.min_chunk_size:
                        # Chunk is big enough, start a new chunk
                        chunks.append({})

                    # Iterate
                    self._json_split(value, new_path, chunks)
        else:
            # handle single item
            self._set_nested_dict(chunks[-1], current_path, data)
        return chunks

    def split_json(
        self,
        json_data,
        convert_lists: bool = False,
    ) -> list[dict]:
        """Splits JSON into a list of JSON chunks"""

        if convert_lists:
            preprocessed_data = self._list_to_dict_preprocessing(json_data)
            chunks = self._json_split(preprocessed_data, None, None)
        else:
            chunks = self._json_split(json_data, None, None)

        # Remove the last chunk if it's empty
        if not chunks[-1]:
            chunks.pop()
        return chunks

    def split_text(
        self,
        json_data: dict[str, Any],
        convert_lists: bool = False,
        ensure_ascii: bool = True,
    ) -> list[str]:
        """Splits JSON into a list of JSON formatted strings"""

        chunks = self.split_json(json_data=json_data, convert_lists=convert_lists)

        # Convert to string
        return [json.dumps(chunk, ensure_ascii=ensure_ascii) for chunk in chunks]
