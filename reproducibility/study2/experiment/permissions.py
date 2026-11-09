"""No launch approval is supplied; diagnostic approval cannot enable evaluation."""
from pathlib import Path
import json,time
ROOT=Path(__file__).resolve().parents[1]
class NotAuthorized(RuntimeError):pass
def require_operation(operation):
    if operation not in ('model_loading','live_inference'):raise NotAuthorized('Operation outside evaluation scope')
    try:
        a=json.loads((ROOT/'runtime/launch_authorization.json').read_text())
        if a.get('status')!='USER_AUTHORIZED_STUDY2_R1' or not a.get('user_authorization_record'):
            raise ValueError('Separate user approval required')
        from integration.frozen import verify_freeze,MODEL_SHA
        from experiment.resource_safeguards import validate_limits
        binding=verify_freeze()
        if a.get('model_manifest_sha256')!=MODEL_SHA:raise ValueError('Wrong model approval')
        plan={'sha256':binding['suite_sha256'],'max_requests':945,'max_output_tokens':148608}
        q=json.loads((ROOT/'runtime/quote.json').read_text())
        h=json.loads((ROOT/'runtime/host_guard.json').read_text())
        local=json.loads((ROOT/'runtime/local_guard.json').read_text())
        result=validate_limits(plan,a,q,h,local,time.time())
        return {'binding':binding,'approval':a,'quote':q,'host':h,'local':local,'validation':result}
    except (OSError,ValueError,KeyError,TypeError) as error:
        raise NotAuthorized('Missing or invalid launch approval/safeguards: '+str(error)) from error
