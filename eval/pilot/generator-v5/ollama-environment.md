# Ollama environment for the M3 pilot (recorded 2026-10-23)

- Installed with: `HOMEBREW_NO_AUTO_UPDATE=1 brew install ollama` (formula, no app, no background service): ollama 0.40.8 (54.1 MB), mlx 0.32.4 (171.4 MB), mlx-c 0.7.0_1 (1 MB)
- Served with: `OLLAMA_HOST=127.0.0.1:11434 OLLAMA_NUM_PARALLEL=1 OLLAMA_MAX_LOADED_MODELS=1 ollama serve` (loopback only; Homebrew's suggested OLLAMA_FLASH_ATTENTION / OLLAMA_KV_CACHE_TYPE not set)
- `ollama --version`: ollama version is 0.40.8
- Model: qwen3:4b, ID 359d7dd4bcda, manifest sha256 31d9857b5705086d352d4d6db04e86c5d0f6a2b5d59a4dc7ce5cdb271ccf9141
- Weights layer: sha256:3e4cb14174460404e7a233e531675303b2fbf7749c02f91864fe311ab6344e4f (2,497,280,480 bytes)
- Pull: before 2026-10-23T02:16:55Z free=27Gi pressure=1 swap_used=1114.00M; after 2026-10-23T02:31:20Z free=25Gi pressure=1 swap_used=1106.00M; ~/.ollama/models 2.3G

`ollama show qwen3:4b`:

```
  Model
    architecture        qwen3          
    parameters          4.0B           
    context length      262144         
    embedding length    2560           
    quantization        Q4_K_M         
    template source     go_template    

  Capabilities
    completion     
    tools          
    thinking       
        levels     true    
        default    true    

  Parameters
    temperature       0.6               
    top_k             20                
    top_p             0.95              
    repeat_penalty    1                 
    stop              "<|im_start|>"    
    stop              "<|im_end|>"      

  License
    Apache License               
    Version 2.0, January 2004    
```
