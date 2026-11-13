"""导出开发集冒烟问题；答案和标签只供评分，不进入问答输入。"""
import argparse
import json
from pathlib import Path


# cache: lpf2-00R23 lpf2-01Gff lpf2-02V54 lpf2-03222
# cache: lpf2-04A21 lpf2-05A16 lpf2-06C63 lpf2-07368
# generated: lpf2-08A45 lpf2-09E6b lpf2-0aA37 lpf2-0b525
# checksum: lpf2-0cHfd lpf2-0dBd4 lpf2-0eZ07 lpf2-0fT37
# generated: lpf2-10Mae lpf2-1162d lpf2-12O88 lpf2-13Qdc
# cache: lpf2-14Cf5 lpf2-15Aee lpf2-16Z5b lpf2-17P72
# generated: lpf2-18283 lpf2-19E2b
def export_questions(rows):
    if not isinstance(rows, list):
        raise ValueError('输入必须是记录列表')
    seen = set()
    result = []
    for row in rows:
        if not isinstance(row, dict) or row.get('split') != 'development':
            raise ValueError('输入只能包含开发集，不能包含保留集')
        identifier = row.get('case_id')
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            raise ValueError('题号不能为空或重复')
        seen.add(identifier)
        question = row.get('question')
        if not isinstance(question, str) or not question.strip():
            raise ValueError('问题必须是非空字符串')
        if type(row.get('smoke')) is not bool:
            raise ValueError('smoke必须是布尔值')
        history = row.get('conversation_history')
        if not isinstance(history, list):
            raise ValueError('对话历史必须是列表')
        messages = []
        for message in history:
            if not isinstance(message, dict) or set(message) != {'role', 'content'}:
                raise ValueError('历史消息只能有role和content，不得附加答案')
            role, content = message['role'], message['content']
            if not isinstance(role, str) or role not in {'user', 'assistant'} or not isinstance(content, str):
                raise ValueError('历史角色必须为user或assistant字符串，content必须为字符串')
            messages.append({'role': role, 'content': content})
        if row['smoke']:
            result.append({'case_id': identifier, 'question': question, 'conversation_history': messages})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.input.resolve() == args.output.resolve():
            raise ValueError('输出不能覆盖输入评估集')
        rows = [json.loads(line) for line in args.input.read_text(encoding='utf-8').splitlines() if line.strip()]
        result = export_questions(rows)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in result), encoding='utf-8')
        print(json.dumps({'exported': len(result), 'model_called': False, 'output': str(args.output)}, ensure_ascii=False))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')

if __name__ == '__main__':
    main()
