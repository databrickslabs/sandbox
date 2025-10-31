"""Generate OpenAPI JSON schema from FastAPI app."""

import json

import click

from server.app import app


@click.command()
@click.option('--output', default='/tmp/openapi.json', help='Output file path')
def main(output: str):
    """Generate OpenAPI JSON schema."""
    openapi_schema = app.openapi()

    with open(output, 'w') as f:
        json.dump(openapi_schema, f, indent=2)

    print(f'OpenAPI schema written to {output}')


if __name__ == '__main__':
    main()
