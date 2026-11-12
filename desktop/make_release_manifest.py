"""Build a local release inventory; never uploads or publishes files.
Example: python3 desktop/make_release_manifest.py --version 0.7.1 --channel beta
 --artifact macos-arm64=/absolute/path/app.zip --output /tmp/release.json
"""
import argparse,hashlib,json,re
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--version',required=True)
parser.add_argument('--channel',choices=['beta','stable'],required=True)
parser.add_argument('--artifact',action='append',required=True,help='platform-architecture=/path/to/file')
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
if not re.fullmatch(r'\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',args.version):parser.error('Versión no válida.')
items=[];seen=set()
for spec in args.artifact:
 platform,separator,value=spec.partition('=')
 if not separator or not re.fullmatch(r'(?:macos|windows|linux)-(?:arm64|x64)',platform) or platform in seen:parser.error('Plataforma/arquitectura no válida o repetida.')
 file=Path(value).expanduser().resolve()
 if not file.is_file():parser.error('No existe el artefacto: '+str(file))
 if file==args.output.resolve():parser.error('La salida no puede sobrescribir un instalador.')
 digest=hashlib.sha256()
 with file.open('rb') as source:
  for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
 items.append({'platform':platform,'file':file.name,'bytes':file.stat().st_size,'sha256':digest.hexdigest(),'download_url':None,'signing_status':'not_verified'})
 seen.add(platform)
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps({'schema_version':1,'product':'voxel-swarm','version':args.version,'channel':args.channel,'published':False,'artifacts':items},indent=2)+'\n')
print('Inventario local generado:',args.output)
