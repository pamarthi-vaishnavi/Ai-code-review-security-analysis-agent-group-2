package com.aicodereview.rag;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Component;

@Component
public class TextChunker {

    private static final int CHUNK_SIZE = 1000;
    private static final int OVERLAP = 200;

    public List<String> splitText(String text) {

        List<String> chunks = new ArrayList<>();

        if (text == null || text.isEmpty()) {
            return chunks;
        }

        int start = 0;

        while (start < text.length()) {

            int end = Math.min(start + CHUNK_SIZE, text.length());

            chunks.add(text.substring(start, end));

            if (end == text.length()) {
                break;
            }

            start = end - OVERLAP;
        }

        return chunks;
    }
}