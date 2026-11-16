"""Start the existing vLLM API server and bind the legacy pre-bound socket to localhost.

Some older vLLM builds bind ('', port) before passing the socket to Uvicorn,
ignoring --host. Only that exact bind is rewritten; nothing in site-packages changes.
"""
import argparse
import os
import runpy
import socket
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, default=18101)
    parser.add_argument('--served-model-name', default='qwen-local')
    parser.add_argument('--gpu-memory-utilization', type=float, default=0.45)
    parser.add_argument('--max-model-len', type=int, default=1024)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('port must be between 1024 and 65535')
    original_bind = socket.socket.bind

    def bind_loopback(sock, address):
        if (isinstance(address, tuple) and len(address) == 2
                and address[0] in ('', '0.0.0.0') and address[1] == args.port):
            address = ('127.0.0.1', args.port)
        return original_bind(sock, address)

    socket.socket.bind = bind_loopback
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    os.environ.setdefault('VLLM_WORKER_MULTIPROC_METHOD', 'spawn')
    sys.argv = ['vllm.entrypoints.openai.api_server', '--host', '127.0.0.1',
                '--port', str(args.port), '--model', args.model,
                '--served-model-name', args.served_model_name, '--dtype', 'half',
                '--max-model-len', str(args.max_model_len),
                '--gpu-memory-utilization', str(args.gpu_memory_utilization),
                '--enforce-eager', '--disable-log-requests',
                '--guided-decoding-backend', 'lm-format-enforcer']
    runpy.run_module('vllm.entrypoints.openai.api_server', run_name='__main__')


if __name__ == '__main__':
    main()
