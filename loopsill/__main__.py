import argparse
from pathlib import Path
import sys

from .demos import DEMO_LABELS
from .errors import MediaError
from .identity import json_bytes
from .offline import export_demo, open_handoff, rehearse
from .server import serve


def main():
    cli = argparse.ArgumentParser(description='本地展陈环播声画接缝工位')
    commands = cli.add_subparsers(dest='action', required=True)
    run = commands.add_parser('serve', help='启动浏览器工作台')
    run.add_argument('--data', type=Path, default=Path('.loopsill-data'))
    run.add_argument('--port', type=int, default=8787)
    demo = commands.add_parser('demo', help='生成可登记的演示素材')
    demo.add_argument('kind', choices=DEMO_LABELS)
    demo.add_argument('output', type=Path)
    verify = commands.add_parser('verify', help='离线核验一圈环带')
    verify.add_argument('bundle', type=Path)
    repeat = commands.add_parser('rehearse', help='物化多圈排练文件')
    repeat.add_argument('bundle', type=Path)
    repeat.add_argument('output', type=Path)
    repeat.add_argument('--turns', required=True, type=int)
    walkthrough = commands.add_parser('walkthrough', help='用合成素材演练一个生产流程')
    from .walkthrough import FLOWS, exercise
    walkthrough.add_argument('workflow', choices=FLOWS)
    args = cli.parse_args()
    try:
        if args.action == 'serve':
            if not 0 <= args.port <= 65535:
                raise MediaError('端口须在 0 到 65535 之间')
            serve(args.data, args.port)
            return 0
        if args.action == 'demo':
            report = export_demo(args.output, args.kind)
        elif args.action == 'verify':
            report, _, _ = open_handoff(args.bundle)
        elif args.action == 'rehearse':
            report = rehearse(args.bundle, args.output, args.turns)
        else:
            report = exercise(args.workflow)
        print(json_bytes(report).decode('utf-8'))
    except (OSError, MediaError) as exc:
        print(f'环映台：{exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
