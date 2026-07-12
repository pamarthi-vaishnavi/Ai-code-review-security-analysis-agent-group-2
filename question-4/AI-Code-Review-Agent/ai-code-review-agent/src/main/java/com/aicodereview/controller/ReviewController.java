package com.aicodereview.controller;

import org.springframework.web.bind.annotation.*;

import com.aicodereview.service.ReviewService;

@RestController
@RequestMapping("/api")
public class ReviewController {

    private final ReviewService reviewService;

    public ReviewController(ReviewService reviewService) {
        this.reviewService = reviewService;
    }

    @PostMapping("/review")
    public String reviewCode(@RequestBody String code) {

        return reviewService.reviewCode(code);

    }
}