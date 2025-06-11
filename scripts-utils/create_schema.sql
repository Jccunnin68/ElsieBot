-- Create elsiebrain database schema

-- Drop tables if they exist (for clean setup)
DROP TABLE IF EXISTS page_metadata CASCADE;
DROP TABLE IF EXISTS wiki_pages CASCADE;

-- Create wiki_pages table
CREATE TABLE wiki_pages (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    raw_content TEXT NOT NULL,
    url VARCHAR(500),
    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    page_type VARCHAR(50),
    ship_name VARCHAR(100),
    log_date DATE,
    content_accessed INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create page_metadata table
CREATE TABLE page_metadata (
    id SERIAL PRIMARY KEY,
    url VARCHAR(500) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    last_crawled TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    crawl_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'active',
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_wiki_pages_title ON wiki_pages(title);
CREATE INDEX idx_wiki_pages_type ON wiki_pages(page_type);
CREATE INDEX idx_wiki_pages_ship ON wiki_pages(ship_name);
CREATE INDEX idx_page_metadata_url ON page_metadata(url);
CREATE INDEX idx_page_metadata_hash ON page_metadata(content_hash);

-- Insert some sample data for testing
INSERT INTO wiki_pages (title, raw_content, url, page_type, ship_name) VALUES
('USS Enterprise (NCC-1701)', 'The USS Enterprise (NCC-1701) was a Constitution-class starship in service during the 23rd century.', 'The USS Enterprise (NCC-1701) was a Constitution-class starship in service during the 23rd century.', 'https://memory-alpha.fandom.com/wiki/USS_Enterprise_(NCC-1701)', 'ship_info', 'enterprise'),
('James T. Kirk', 'James Tiberius Kirk was a renowned Starfleet captain who commanded the USS Enterprise.', 'James Tiberius Kirk was a renowned Starfleet captain who commanded the USS Enterprise.', 'https://memory-alpha.fandom.com/wiki/James_T._Kirk', 'personnel', 'enterprise'),
('Starfleet', 'Starfleet is the deep-space exploratory and peacekeeping armada of the United Federation of Planets.', 'Starfleet is the deep-space exploratory and peacekeeping armada of the United Federation of Planets.', 'https://memory-alpha.fandom.com/wiki/Starfleet', 'general', null);

-- Show tables created
\dt

-- Show sample data
SELECT COUNT(*) as total_pages FROM wiki_pages;
SELECT page_type, COUNT(*) as count FROM wiki_pages GROUP BY page_type;

COMMIT; 