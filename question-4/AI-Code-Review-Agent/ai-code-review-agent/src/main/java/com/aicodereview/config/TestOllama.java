package com.aicodereview;

import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.ollama.OllamaChatModel;

public class TestOllama {

    public static void main(String[] args) {

        ChatModel model = OllamaChatModel.builder()
                .baseUrl("http://localhost:11434")
                .modelName("deepseek-coder")
                .temperature(0.2)
                .build();

        String response = model.chat("Say Hello");

        System.out.println(response);
    }
}