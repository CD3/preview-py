import asyncio
import subprocess
try:
    from pymsgbox import *
except:
    def alert(text):
        print(text)


async def async_run(cmd,*args):
    proc = await asyncio.create_subprocess_exec( cmd, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    return proc

def sync_run(cmd,*args):
    results = subprocess.run( [cmd, *args], stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    return results

