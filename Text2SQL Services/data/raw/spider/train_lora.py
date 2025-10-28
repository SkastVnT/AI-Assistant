# -*- coding: utf-8 -*-
import os
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
import torch

BASE_MODEL = os.environ.get("BASE_MODEL", "defog/sqlcoder-7b-2")
DATA_DIR = os.environ.get("DATA_DIR", "models/spider_pretrain")
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", "models/sqlcoder-spider-lora")

USE_4BIT = True  # đặt False nếu không có bitsandbytes


def format_sample(ex):
    # ghép input + output thành training text cho causal LM
    # Mục tiêu: model thấy prompt và học sinh chuỗi "### SQL: ...;"
    return {"text": ex["input"] + "\n" + ex["output"]}


def main():
    dataset = load_dataset("json", data_files={"train": "data/yourset/train.jsonl"})

    dataset = dataset.map(format_sample, remove_columns=dataset["train"].column_names)

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=False)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=2048)

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

    print("Loading base model...")
    if USE_4BIT:
        from transformers import BitsAndBytesConfig

        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, quantization_config=bnb_config, device_map="auto"
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, torch_dtype=torch.bfloat16, device_map="auto"
        )

    model = prepare_model_for_kbit_training(model)
    lora_cfg = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    args = TrainingArguments(
        output_dir=OUTPUT_DIR,
        num_train_epochs=2,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        per_device_eval_batch_size=1,
        eval_steps=500,
        save_steps=500,
        logging_steps=50,
        learning_rate=2e-4,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        bf16=True,
        optim="paged_adamw_32bit",
        gradient_checkpointing=True,
        # ddp_find_unused_parameters nếu bản bạn có, giữ lại; nếu không thì bỏ
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=tokenized["train"],
        data_collator=data_collator,
    )

    trainer.train()
    trainer.save_model(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"Saved LoRA adapter -> {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
