from __future__ import absolute_import
from __future__ import print_function
import sys
import argparse
import json
import copy
from elasticsearch import Elasticsearch
from damn_at.utilities import unique_asset_id_reference_from_fields


'''
pt a ../peragro-test-files/mesh/blender/cube1.blend -f json-pretty\
 | pt index elastic\
 | pt index stats
'''


def index(asset):
    es = Elasticsearch()
    ret = es.index(index='damn', doc_type='asset',
                   id=asset['id'], body=asset)
    print(ret)


def create_argparse(parser, subparsers):
    subparse = subparsers.add_parser(
        "index",  # aliases=("i",),
        help="Anything to do with indexing",
    )
    subsubparsers = subparse.add_subparsers(
        title='subcommands',
        description='valid subcommands',
        help='additional help',
    )
    create_argparse_elastic(subparse, subsubparsers)
    create_argparse_generate_search(subparse, subsubparsers)
    create_argparse_stats(subparse, subsubparsers)


def create_argparse_elastic(parser, subparsers):
    subparse = subparsers.add_parser(
        "elastic",  # aliases=("transform",),
        help="index the given file description to elasticsearch",
    )
    subparse.add_argument(
        'infile', nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin)

    def transform(args):
        data = args.infile.read()
        data = json.loads(data)
        file_hash = data["file"]["hash"]
        assets = []
        file_copy = copy.deepcopy(data)
        file_copy['metadata'] = file_copy.get('metadata', {})
        del file_copy['assets']
        del file_copy['metadata']
        for asset in data['assets']:
            subname = asset['asset']['subname']
            mimetype = asset['asset']['mimetype']
            id = unique_asset_id_reference_from_fields(file_hash, subname, mimetype)
            a = {'id': id, 'file': file_copy}
            asset['metadata'] = asset.get('metadata', {})
            a.update(asset)
            assets.append(a)
        for asset in assets:
            index(asset)

    subparse.set_defaults(
        func=lambda args:
        transform(args),
    )


def create_argparse_generate_search(parser, subparsers):
    subparse = subparsers.add_parser(
        "generate-search",  # aliases=("transform",),
        help="Generate a faceted search",
    )

    def search(args):
        from damn_at import Analyzer
        from damn_at.utilities import get_metadatavalue_fieldname
        m = Analyzer().get_supported_metadata()
        ret = {'aggs': {},
               'query': {'match_all': {}},
               'from': 3, 'size': 1, }
        for mime, metas in list(m.items()):
            for meta, type in metas:
                field_name = get_metadatavalue_fieldname(type)
                ret['aggs'][meta] = {'terms': {'field': 'metadata.'+meta+'.'+field_name}}

        print(json.dumps(ret, indent=2))

    subparse.set_defaults(
        func=lambda args:
        search(args),
    )


def create_argparse_stats(parser, subparsers):
    subparse = subparsers.add_parser(
        "stats",  # aliases=("transform",),
        help="Generate stats from an ES bulk upload",
    )
    subparse.add_argument(
        'infile', nargs='?',
        type=argparse.FileType('r'),
        default=sys.stdin)

    def stats(args):
        data = args.infile.read()
        data = json.loads(data)
        print('Uploaded: {0:>6}'.format(len(data['items'])))
        print('Errors:   {0:>6}'.format(data['errors']))
        print('took:     {:>6} ms'.format(data['took']))
        if data['errors']:
            sys.exit(1)

    subparse.set_defaults(
        func=lambda args:
        stats(args),
    )
