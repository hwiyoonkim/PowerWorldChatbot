# PowerWorld Assistant with LLaMA 2-13B + LoRA Fine-Tuning

## Overview

This project builds an AI-powered assistant for analyzing PowerWorld `.pwb` case files using a local instance of the **LLaMA 2-13B-Instruct** model, enhanced with **LoRA-based fine-tuning**. The assistant provides natural language summaries and Q&A capabilities about electric power system data extracted from PowerWorld via SimAuto.

## Features

- Upload `.pwb` files via web UI
- Auto-convert to `.aux` using PowerWorld SimAuto
- Extract and parse power system data (buses, branches, generators, etc.)
- Build knowledge base (KB) from the parsed AUX
- Summarize and answer questions using locally hosted LLaMA 2-13B model
- Use LoRA for domain-specific fine-tuning (efficient + low memory usage)

## Architecture

```
[User Uploads .pwb] ──► [Flask Backend]
                          │
                          ▼
         [SimAuto → AUX Export (full_case_export.aux)]
                          │
                          ▼
     [Parse AUX → Build KB → Inject into LLaMA Prompt]
                          │
                          ▼
      [LLaMA 2-13B-Instruct + LoRA] → [Answer / Summarize]
                          │
                          ▼
              [Web UI: Chat + Table Viewer + Downloads]
```

## Model Info

- **Model**: `meta-llama/Llama-2-13b-hf`
- **Type**: Instruction-tuned large language model
- **Deployment**: Local with `transformers` and `torch`
- **Hardware**: NVIDIA H100 NVL (96GB VRAM)
- **CUDA Version**: 12.9

## Why LoRA?

LoRA (Low-Rank Adaptation) is a parameter-efficient fine-tuning method. It allows training only a small number of parameters while keeping the base model frozen.

**Benefits**:

- Requires less GPU memory and training time
- Ideal for domain adaptation (e.g., power systems)
- Fine-tune without modifying the entire model
- Easily load/unload adapters at inference time

## Fine-Tuning Motivation

The assistant initially produced hallucinated responses due to lack of domain grounding. To address this, LoRA fine-tuning is applied using data generated from real `.aux` files and power systems textbooks.

### Example Instruction Format

```json
{
  "instruction": "How many buses are in the system?",
  "input": "AUX file contains 240 buses.",
  "output": "There are 240 buses in the system."
}
```

## Dataset Strategy

- Use exported `.aux` files from PowerWorld as the base source
- Extract structured knowledge from Bus, Branch, Gen, Load tables
- Convert into instruction-tuning dataset (JSON format)
- Augment with questions and summaries from textbooks or manuals

## Getting Started

1. Clone the repository and set up virtual environment
2. Install dependencies: `pip install -r requirements.txt`
3. Place your `.pwb` files into the `/uploads` directory
4. Run the app: `python app.py`
5. Interact through the browser UI (`http://127.0.0.1:5000`)


## License

This project is for educational and research purposes only.
