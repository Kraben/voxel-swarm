"""Build a signed MusicKit app after the user configures their Apple team.
Usage: python3 prepare_music.py --team ABCDE12345 [--bundle-id com.example.vox.music]
This uses Xcode's account/keychain. No developer .p8 key is needed or copied.
"""
import argparse,os,plistlib,re,shutil,subprocess
from pathlib import Path
from uuid import uuid4
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--team',required=True)
parser.add_argument('--bundle-id',default='com.voxelswarm.desktop.music')
args=parser.parse_args()
if not re.fullmatch(r'[A-Z0-9]{10}',args.team):parser.error('El Team ID debe contener 10 letras/números.')
if not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+){2,}',args.bundle_id):parser.error('Bundle ID no válido.')
root=Path(__file__).resolve().parents[1];desktop=root/'desktop'
project=root/'macos'/'MusicKitBridge'/'VoxelMusic.xcodeproj'
derived=root/'work'/'musickit-build'
env=os.environ.copy()
if 'DEVELOPER_DIR' not in env and Path('/Applications/Xcode.app/Contents/Developer').is_dir():env['DEVELOPER_DIR']='/Applications/Xcode.app/Contents/Developer'
subprocess.run(['xcrun','xcodebuild','-project',str(project),'-scheme','VoxelMusic','-configuration','Debug','-derivedDataPath',str(derived),'-allowProvisioningUpdates','DEVELOPMENT_TEAM='+args.team,'PRODUCT_BUNDLE_IDENTIFIER='+args.bundle_id,'build'],env=env,check=True)
source=derived/'Build'/'Products'/'Debug'/'VoxelMusic.app'
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(source)],check=True)
identity=subprocess.run(['/usr/bin/codesign','-dv','--verbose=4',str(source)],capture_output=True,text=True,check=True)
if 'TeamIdentifier='+args.team not in identity.stderr:raise SystemExit('La firma no pertenece al equipo indicado. No se instalará el componente.')
with (source/'Contents/Info.plist').open('rb') as f:info=plistlib.load(f)
if info.get('CFBundleIdentifier')!=args.bundle_id:raise SystemExit('El Bundle ID compilado no coincide.')
staging=desktop/('music-staging-'+uuid4().hex);shutil.copytree(source,staging)
target=desktop/'music-runtime'/'VoxelMusic.app'
if target.exists():shutil.rmtree(target)
staging.rename(target)
print('MusicKit firmado preparado. Reinicia Vóxeles para conectarlo desde Ajustes. Para compartirlo con terceros, utiliza firma Developer ID y notarización; este build es de desarrollo.')
