package com.aicodereview.service;

import dev.langchain4j.model.chat.ChatModel;
import org.springframework.stereotype.Service;

@Service
public class ReviewService {

    private final ChatModel model;

    public ReviewService(ChatModel model) {
        this.model = model;
    }

    public String reviewCode(String code) {

        String prompt = """
        Review this Java code.
        Find:
        1. Bugs
        2. Security Issues
        3. Performance Issues
        4. Best Practice Improvements

        Code:
        %s
        """.formatted(code);

        return model.chat(prompt);
    }
}