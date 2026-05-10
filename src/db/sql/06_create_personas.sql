CREATE TABLE IF NOT EXISTS personas (
    id SERIAL PRIMARY KEY,
    session_id UUID
    REFERENCES sessions(session_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    name VARCHAR(50),
    age INT,
    generation TEXT,
    gender VARCHAR(20),
    country VARCHAR(50),
    mother_language VARCHAR(50),
    second_languages TEXT[],  -- Array of languages
    archetype TEXT,
    archetype_description TEXT,
    social_tendency VARCHAR(50),
    attention_span VARCHAR(20),
    mood VARCHAR(50),
    is_friend BOOLEAN DEFAULT FALSE,
    system_prompt TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);