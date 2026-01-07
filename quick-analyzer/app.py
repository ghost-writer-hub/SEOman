#!/usr/bin/env python3
from flask import Flask, request, jsonify
from pyseoanalyzer import analyze
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/health')
def health():
    return {'status': 'ok'}


@app.route('/analyze')
def analyze_site():
    url = request.args.get('url')
    if not url:
        return {'error': 'url parameter required'}, 400
    
    logger.info(f'Analyzing: {url}')
    try:
        result = analyze(url, follow_links=False)
        return jsonify(result)
    except Exception as e:
        logger.error(f'Analysis failed: {e}')
        return {'error': str(e)}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
