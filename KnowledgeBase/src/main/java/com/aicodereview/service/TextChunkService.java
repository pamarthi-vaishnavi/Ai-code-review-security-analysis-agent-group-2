package com.aicodereview.service;

import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class TextChunkService {

    private static final int CHUNK_SIZE = 1000;

    public List<String> chunkDocuments(List<String> documents) {

        List<String> chunks = new ArrayList<>();

        for (String document : documents) {

            if (document == null || document.isBlank()) {
                continue;
            }

            int start = 0;

            while (start < document.length()) {

                int end = Math.min(start + CHUNK_SIZE, document.length());

                chunks.add(document.substring(start, end));

                start = end;
            }
        }

        System.out.println("Total Chunks Created: " + chunks.size());

        return chunks;
    }
}