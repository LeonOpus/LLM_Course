"""M11 命令行入口。run 可能调用真实模型；review/report/compare 不请求模型。"""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from urllib.request import Request, urlopen

# generated: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# revision: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# generated: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# revision: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# generated: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# cache: lpf2-18283 lpf2-19E2b
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluation.runtime import run_suite, compare_runs
from evaluation.reporting import load_run, review_template, score_run, render_report


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def http_client(base):
    parts = urlparse(base)
    if parts.scheme not in {'http', 'https'} or parts.hostname not in {'localhost', '127.0.0.1', '::1'} or parts.username or parts.password or parts.query or parts.fragment:
        raise ValueError('本节仅连接 localhost/127.0.0.1/::1 后端，不在地址里放凭证')
    base = base.rstrip('/')
    def request(path, body=None):
        payload = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
        req = Request(base + path, data=payload, headers={'Content-Type': 'application/json'})
        with urlopen(req, timeout=180) as response:
            return json.load(response)
    return request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('run', help='真实调用本地 RAG 后端，逐题保存；可能产生云费用')
    p.add_argument('--materials', default='materials/m06')
    p.add_argument('--suite', choices=['smoke', 'development'], default='smoke')
    p.add_argument('--base-url', default='http://127.0.0.1:8000')
    p.add_argument('--strategy', choices=['baseline', 'rerank'], default='baseline')
    p.add_argument('--top-k', type=int, default=10);p.add_argument('--final-k', type=int, default=5)
    p.add_argument('--output', required=True)
    p.add_argument('--require-index-profile',action='store_true',help='M12B起使用：缺少或变更实际索引配置时不得标为可比较')
    p.add_argument('--require-retrieval-profile',action='store_true',help='M13A起使用：保存并校验实际召回模式与融合参数')
    p.add_argument('--require-query-profile',action='store_true',help='M13B起使用：检查实际查询改写配置全批一致')
    p.add_argument('--require-generation-profile',action='store_true',help='M14起使用：检查实际生成策略与提示版本全批一致')
    p.add_argument('--require-context-profile',action='store_true',help='M18A起使用：校验原文补全策略与字符预算全批一致')
    p.add_argument('--require-source-scope-profile',action='store_true',help='M24起：核对实际来源过滤配置全批一致')
    p.add_argument('--run-label', default='学员 RAG 运行（服务真实性须由运行者核对）')
    p = sub.add_parser('review-template', help='生成全为待复核的 JSON，禁止默认全对')
    p.add_argument('--run', required=True);p.add_argument('--output', required=True)
    p = sub.add_parser('report', help='校验复核文件，输出只读 HTML 和 JSON')
    p.add_argument('--run', required=True);p.add_argument('--reviews');p.add_argument('--output', required=True)
    p = sub.add_parser('compare', help='重新读取原始记录和评分后逐题比较')
    p.add_argument('--left', required=True);p.add_argument('--right', required=True)
    p.add_argument('--left-reviews', required=True);p.add_argument('--right-reviews', required=True)
    p.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'run':
            materials = Path(args.materials)
            package = read(materials / 'package.json')
            cases = [json.loads(line) for line in (materials / 'development.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
            if args.suite == 'smoke':cases = [c for c in cases if c.get('smoke') is True]
            request = http_client(args.base_url)
            result = run_suite(cases, package['documents'], {'strategy':args.strategy,'top_k':args.top_k,'final_k':args.final_k,'run_label':args.run_label,'require_index_profile':args.require_index_profile,'require_retrieval_profile':args.require_retrieval_profile,'require_query_profile':args.require_query_profile,'require_generation_profile':args.require_generation_profile,'require_context_profile':args.require_context_profile,'require_source_scope_profile':args.require_source_scope_profile},
                args.output, lambda: request('/api/documents'), lambda body: request('/api/ask', body))
            print(json.dumps({'planned':result['planned'],'execution_counts':result['execution_counts'],
                'review_status':result['review_status'],'comparable':result['manifest']['comparable']}, ensure_ascii=False, indent=2))
        elif args.command == 'review-template':
            _, cases, records = load_run(args.run)
            by_id = {r['case_id']:r for r in records}
            templates = [review_template(c, by_id[c['case_id']]) for c in cases]
            write_new(args.output, [t for t in templates if t is not None])
            print('已生成待复核模板；true/false/null 分别表示通过、未通过、尚未确认。')
        elif args.command == 'report':
            output = Path(args.output)
            if output.exists():raise ValueError('报告目录已存在，请换新目录')
            result, cases, records = score_run(args.run, read(args.reviews) if args.reviews else [])
            output.mkdir(parents=True, exist_ok=False)
            write_new(output / 'summary.json', result)
            (output / 'report.html').write_text(render_report(result, cases, records), encoding='utf-8')
            print('报告已生成：' + str(output / 'report.html'))
        else:
            left, _, _ = score_run(args.left, read(args.left_reviews))
            right, _, _ = score_run(args.right, read(args.right_reviews))
            write_new(args.output, compare_runs(left, right))
            print('配对结果已保存；先看 pending，再看 gain/regression。')
    except (ValueError, OSError, KeyError, TypeError) as error:
        # 不回显 HTTP 错误正文、密钥或未知异常内容。
        if isinstance(error, ValueError):parser.exit(1, str(error) + '\n')
        parser.exit(1, f'{type(error).__name__}：检查路径、文件格式和后端状态。\n')

if __name__ == '__main__':main()
