-- AIgenda schema for MySQL / MariaDB (XAMPP). Created automatically by main.py on first run.
-- Engine InnoDB is required for foreign keys.

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(120) NOT NULL,
  program       VARCHAR(120) NOT NULL DEFAULT 'Student',
  email         VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(200) NOT NULL,
  is_test       TINYINT(1) NOT NULL DEFAULT 0,   -- 1 = developer/test account, excluded from model training
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sessions (
  token      VARCHAR(64) PRIMARY KEY,
  user_id    INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-02: one habit profile per student. The 1-5 self-ratings are optional model inputs (NULL = survey average).
CREATE TABLE IF NOT EXISTS habit_profiles (
  user_id      INT PRIMARY KEY,
  wake_hour    TINYINT NOT NULL DEFAULT 6,
  sleep_hour   TINYINT NOT NULL DEFAULT 23,
  class_start  TINYINT NOT NULL DEFAULT 8,
  class_end    TINYINT NOT NULL DEFAULT 12,
  chronotype   ENUM('morning','afternoon','evening') NOT NULL DEFAULT 'morning',
  adherence    TINYINT NULL,
  distraction  TINYINT NULL,
  stress_sleep TINYINT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CHECK (wake_hour BETWEEN 0 AND 23 AND sleep_hour BETWEEN 0 AND 23)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hobbies (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name    VARCHAR(80) NOT NULL,
  UNIQUE KEY uq_hobby (user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-03: ranked subjects (subject_rank 1 = highest priority)
CREATE TABLE IF NOT EXISTS subjects (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  name         VARCHAR(120) NOT NULL,
  subject_rank INT NOT NULL,
  UNIQUE KEY uq_subject (user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-04 / UC-05: generated schedule. logged = 1 once its outcome was copied into activity_log.
CREATE TABLE IF NOT EXISTS schedule_items (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  day          DATE NOT NULL,
  hour         TINYINT NOT NULL,
  label        VARCHAR(120) NOT NULL,
  kind         ENUM('study','hobby','class','rest') NOT NULL,
  subject_rank TINYINT NULL,
  done         TINYINT(1) NOT NULL DEFAULT 0,
  source       ENUM('ai','manual') NOT NULL DEFAULT 'ai',
  logged       TINYINT(1) NOT NULL DEFAULT 0,
  INDEX idx_items_user_day (user_id, day),
  INDEX idx_items_logging (logged, day),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-06 / UC-10: goals and milestones
CREATE TABLE IF NOT EXISTS goals (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id  INT NOT NULL,
  title    VARCHAR(200) NOT NULL,
  progress TINYINT NOT NULL DEFAULT 0,
  due_date DATE NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CHECK (progress BETWEEN 0 AND 100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Final outcome of every study block (completed OR skipped). This table is the model's real training data.
CREATE TABLE IF NOT EXISTS activity_log (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  day          DATE NOT NULL,
  hour         TINYINT NOT NULL,
  kind         VARCHAR(20) NOT NULL DEFAULT 'study',
  priority     TINYINT NULL,
  day_load     TINYINT NULL,
  in_peak      TINYINT(1) NOT NULL,
  adherence    TINYINT NULL,
  distraction  TINYINT NULL,
  stress_sleep TINYINT NULL,
  completed    TINYINT(1) NOT NULL,
  logged_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_log_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit trail of model (re)training runs
CREATE TABLE IF NOT EXISTS model_runs (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  trained_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  source        ENUM('synthetic','retrain') NOT NULL,
  real_rows     INT NOT NULL DEFAULT 0,
  test_rows     INT NULL,
  test_accuracy DECIMAL(5,3) NULL,
  test_auc      DECIMAL(5,3) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
