import marimo

__generated_with = "0.21.1"
app = marimo.App()


@app.cell
def _():
    import huggingface_hub

    #from huggingface_hub import login, upload_folder, hf_hub_download


    # snapshot_download(repo_id="google/fleurs", repo_type="dataset")


    # huggingface_hub.snapshot_download(repo_id="Apokryf/minimap-of-uce", repo_type="dataset", local_dir="./imperialmap")

    # #huggingface_hub.upload_folder(folder_path="./minimap-of-uce", repo_id="Apokryf/minimap-of-uce", repo_type="dataset")



    # map_of_empire = load_dataset("Apokryf/minimap-of-uce", data_dir="./imperialmap")

    # map_of_empire.push_to_hub("Apokryf/minimap-of-uce")
    return (huggingface_hub,)


@app.cell
def _(huggingface_hub):
    huggingface_hub.login()
    return


@app.cell
def _(huggingface_hub):
    huggingface_hub.snapshot_download(
        repo_id="Apokryf/minimap-of-uce", 
        repo_type="dataset", 
        local_dir="./imperialmap"
    )
    return


@app.cell
def _(huggingface_hub):
    huggingface_hub.upload_folder(
        folder_path="./imperialmap", 
        repo_id="Apokryf/minimap-of-uce", 
        repo_type="dataset"
    )
    return


@app.cell
def _():
    import os

    os.mkdir("./imperialmap/store-areas")

    #os.listdir("./imperialmap/federations")
    return


if __name__ == "__main__":
    app.run()

