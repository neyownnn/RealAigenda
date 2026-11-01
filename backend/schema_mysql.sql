-- AIgenda MySQL / MariaDB schema (works on XAMPP). Created automatically by main.py on first run.
-- Manual import: phpMyAdmin -> create database `aigenda` (utf8mb4) -> Import this file.

CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  name          VARCHAR(100) NOT NULL,
  program       VARCHAR(100) NOT NULL DEFAULT 'Student',
  email         VARCHAR(190) NOT NULL UNIQUE,
  password_hash VARCHAR(200) NOT NULL,
  is_test       TINYINT(1)   NOT NULL DEFAULT 0,   -- 1 = tester account, excluded from model retraining
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sessions (
  token      VARCHAR(64) PRIMARY KEY,
  user_id    INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-02: habits + the three self-ratings that are also Random Forest features (same wording as the survey)
CREATE TABLE IF NOT EXISTS habit_profiles (
  user_id      INT PRIMARY KEY,
  wake_hour    TINYINT NOT NULL DEFAULT 6,
  sleep_hour   TINYINT NOT NULL DEFAULT 23,
  class_start  TINYINT NOT NULL DEFAULT 8,
  class_end    TINYINT NOT NULL DEFAULT 12,
  chronotype   ENUM('morning','afternoon','evening') NOT NULL DEFAULT 'morning',
  adherence    TINYINT NOT NULL DEFAULT 3,         -- 1-5 "I follow my study schedule consistently"
  distraction  TINYINT NOT NULL DEFAULT 3,         -- 1-5 "I get easily distracted by social media"
  stress_sleep TINYINT NOT NULL DEFAULT 3,         -- 1-5 "Stress or lack of sleep affects my concentration"
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hobbies (
  id      INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  name    VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_hobby (user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-03: ranked subjects (priority_rank 1 = most important)
CREATE TABLE IF NOT EXISTS subjects (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  user_id       INT NOT NULL,
  name          VARCHAR(150) NOT NULL,
  priority_rank INT NOT NULL,
  UNIQUE KEY uq_subject (user_id, name),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- UC-04/05: today's and past schedules. rank/in_peak are frozen at generation time so the outcome row is faithful.
CREATE TABLE IF NOT EXISTS schedule_items (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  day          DATE NOT NULL,
  hour         TINYINT NOT NULL,
  label        VARCHAR(150) NOT NULL,
  kind         ENUM('study','hobby','class','rest') NOT NULL,
  done         TINYINT(1) NOT NULL DEFAULT 0,
  subject_rank TINYINT NULL,
  in_peak      TINYINT(1) NOT NULL DEFAULT 0,
  logged       TINYINT(1) NOT NULL DEFAULT 0,      -- 1 once its outcome is copied to activity_log
  INDEX idx_user_day (user_id, day),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS goals (
  id       INT AUTO_INCREMENT PRIMARY KEY,
  user_id  INT NOT NULL,
  title    VARCHAR(200) NOT NULL,
  progress TINYINT NOT NULL DEFAULT 0,
  due_date DATE NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- THE LEARNING TABLE: one row per study block whose day has ended (completed = 1 done, 0 skipped).
-- Columns match the Random Forest features exactly.
CREATE TABLE IF NOT EXISTS activity_log (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  day          DATE NOT NULL,
  hour         TINYINT NOT NULL,
  in_peak      TINYINT(1) NOT NULL,
  priority     TINYINT NOT NULL,
  day_load     TINYINT NOT NULL,                   -- study blocks scheduled that day
  adherence    TINYINT NOT NULL,
  distraction  TINYINT NOT NULL,
  stress_sleep TINYINT NOT NULL,
  completed    TINYINT(1) NOT NULL,
  logged_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_user (user_id),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Audit trail of every retraining (useful evidence for the paper)
CREATE TABLE IF NOT EXISTS model_runs (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  trained_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rows_real  INT NOT NULL,
  accuracy   FLOAT NULL,
  roc_auc    FLOAT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
