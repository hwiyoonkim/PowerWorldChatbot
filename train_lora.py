from peft import LoraConfig, get_peft_model
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import load_dataset

model_id = "meta-llama/Llama-2-13b-hf"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", torch_dtype=torch.float16)

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
model = get_peft_model(model, lora_config)

dataset = load_dataset("json", data_files="training/dataset.jsonl", split="train")

def preprocess(ex):
    prompt = f"<s>[INST] <<SYS>>\\nUse this power system info.\\n<</SYS>>\\n{ex['instruction']}\\n{ex['input']} [/INST] {ex['output']}"
    return tokenizer(prompt, padding="max_length", truncation=True, max_length=1024)

tokenized = dataset.map(preprocess, batched=True)

training_args = TrainingArguments(
    output_dir="llama2_lora_out",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    num_train_epochs=3,
    learning_rate=2e-5,
    logging_steps=10,
    save_steps=100,
    save_total_limit=2,
    bf16=True
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized,
    tokenizer=tokenizer
)

trainer.train()
model.save_pretrained("llama2_lora_out")
