CREATE TABLE Users (
    UserID INTEGER PRIMARY KEY,
    First_name VARCHAR(250),
    Last_name VARCHAR(250),
    Username VARCHAR(250),
    TelegramId INTEGER
);

CREATE TABLE ArmLocation (
    ArmLocationID INTEGER PRIMARY KEY,
    LocationName VARCHAR(100)
);

CREATE TABLE BodyPositions (
    BodyPositionID INTEGER PRIMARY KEY,
    PositionName VARCHAR(100)
);

CREATE TABLE Comments (
    CommentID INTEGER PRIMARY KEY,
    CommentText TEXT
);

CREATE TABLE Measurements (
    MeasurementID INTEGER PRIMARY KEY,
    UserID INTEGER,
    ArmLocationID INTEGER,
    BodyPositionID INTEGER,
    CommentID INTEGER,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (ArmLocationID) REFERENCES ArmLocation(ArmLocationID),
    FOREIGN KEY (BodyPositionID) REFERENCES BodyPositions(BodyPositionID),
    FOREIGN KEY (CommentID) REFERENCES Comments(CommentID)
);

CREATE TABLE MeasureDetails (
    MeasureDetailID INTEGER PRIMARY KEY,
    MeasurementID INTEGER,
    SystolicPressure INTEGER,
    DiastolicPressure INTEGER,
    Pulse INTEGER,
    FOREIGN KEY (MeasurementID) REFERENCES Measurements(MeasurementID)
);

-- Seed reference data for ArmLocation
INSERT INTO ArmLocation (ArmLocationID, LocationName) VALUES
    (1, 'Левая рука'),
    (2, 'Правая рука'),
    (3, 'Левое плечё'),
    (4, 'Правое плечё'),
    (5, 'Не указано');

-- Seed reference data for BodyPositions
INSERT INTO BodyPositions (BodyPositionID, PositionName) VALUES
    (1, 'Стоя'),
    (2, 'Сидя'),
    (3, 'Лёжа'),
    (4, 'Полу лёжа'),
    (5, 'Не указано');
