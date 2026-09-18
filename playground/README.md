# playground

Scratch space, one folder per team member. Try things here — prompts, API pokes, voice/SDK spikes, notebooks — without touching the real app.

| Folder | Member |
|---|---|
| `luis/` | Luis González |
| `fran/` | Jose Francisco Udaeta Arce |
| `alejandro/` | Alejandro Flores Sepulveda |
| `marcos/` | Marcos Jaen Garcia |

Rules:

- **Only edit your own folder.** That way nobody hits merge conflicts here.
- **Nothing in `app/`, `lib/` or `tests/` imports from `playground/`.** When a spike works, move it into its slice properly.
- **No secrets.** Read keys from `.env` (gitignored), never paste them into files here.
- `ruff` skips this folder, so `make verify` stays green whatever you leave in it.
