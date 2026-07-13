package com.aicodereview.service;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ChatService {

    private final SimilaritySearchService similaritySearchService;
    private final ChatClient chatClient;

    public ChatService(SimilaritySearchService similaritySearchService,
                       ChatClient.Builder chatClientBuilder) {

        this.similaritySearchService = similaritySearchService;
        this.chatClient = chatClientBuilder.build();
    }

    public String askQuestion(String question) {

        List<String> context = similaritySearchService.search(question, 3);

        String prompt = """
                You are a Secure Coding Expert.

                Answer the user's question ONLY using the context below.

                Context:
                %s

                Question:
                %s
                """.formatted(String.join("\n\n", context), question);

        System.out.println("ChatService called...");

        return chatClient.prompt()
                .user(prompt)
                .call()
                .content();
    }
}