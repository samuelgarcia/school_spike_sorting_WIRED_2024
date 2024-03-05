from pathlib import Path

import spikeinterface.full as si

base_folder = Path("/home/samuel/DataSpikeSorting/WIRED_SI_tutos/")

neuralynx_folder = base_folder / "Neuralynx"
out_folder = base_folder / "Binary"

job_kwargs = dict(n_jobs=-1, progress_bar=True, chunk_duration="1s")

def conver_all():
    for folder in neuralynx_folder.glob("**/ieeg"):
        print()
        print(folder)
        new_folder = out_folder / folder.relative_to(neuralynx_folder)
        
        if new_folder.exists():
            continue
        new_folder.parent.mkdir(parents=True, exist_ok=True)
        rec = si.read_neuralynx(folder)
        rec_conc = si.concatenate_recordings([rec])
        # print(rec_conc)
        rec_conc.save(folder=new_folder, format="binary", **job_kwargs)



if __name__ == "__main__":
    conver_all()

