package com.aicodereview.controller;

import com.aicodereview.dto.ChatRequest;
import com.aicodereview.dto.ChatResponse;
import com.aicodereview.service.ChatService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/chat")
@CrossOrigin("*")
public class ChatController {

    private final ChatService chatService;

    public ChatController(ChatService chatService) {
        this.chatService = chatService;
    }

    @PostMapping
    public ChatResponse chat(@RequestBody ChatRequest request) {

        String answer = chatService.askQuestion(request.getQuestion());

        return new ChatResponse(answer);
    }
}