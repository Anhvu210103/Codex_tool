import argparse
import json
import logging
import time
from pathlib import Path

from .core import process
from .gmail import authorize, messages


def main():
    parser = argparse.ArgumentParser(description='Gmail → rules → daily Markdown notebook')
    parser.add_argument('command', choices=['demo', 'auth', 'once', 'watch'])
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--input', default='examples/messages.json')
    parser.add_argument('--credentials', default='.local/credentials.json')
    parser.add_argument('--token', default='.local/token.json')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.command == 'auth':
        authorize(args.credentials, args.token)
        return
    config_path = Path(args.config).resolve()
    config = json.loads(config_path.read_text(encoding='utf-8'))
    config['data_dir'] = str(config_path.parent / config['data_dir'])
    if int(config.get('interval_seconds', 1800)) < 1:
        raise ValueError('interval_seconds must be positive')
    if args.command == 'demo':
        # Demo and real mail keep separate stores, even when IDs happen to match.
        config['data_dir'] = str(Path(config['data_dir']) / 'demo')
        count = process(json.loads(Path(args.input).read_text(encoding='utf-8')), config, 'demo')
        print(f'Added {count} notes. Output: {config["data_dir"]}/notebooks')
        return
    while True:
        try:
            count = process(messages(config, args.credentials, args.token), config, 'gmail')
            logging.info('Added %d notes', count)
        except Exception as error:
            # Do not log response bodies, request headers, tokens or email text.
            logging.error('Polling failed (%s); check credentials, network and configuration.', type(error).__name__)
            if args.command == 'once':
                raise SystemExit(1) from None
        if args.command == 'once':
            break
        time.sleep(int(config.get('interval_seconds', 1800)))


if __name__ == '__main__':
    main()
