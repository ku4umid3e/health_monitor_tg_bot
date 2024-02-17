-- Таблица "Users"
CREATE TABLE Users (
    UserID INTEGER PRIMARY KEY,
    First_name VARCHAR(250),
    Last_name VARCHAR(250),
    Username VARCHAR(250),
    TelegramId INTEGER
);

-- Таблица "ArmPositions"
CREATE TABLE ArmPositions (
    ArmPositionID INTEGER PRIMARY KEY,
    PositionName VARCHAR(100)
);

-- Таблица "BodyPositions"
CREATE TABLE BodyPositions (
    BodyPositionID INTEGER PRIMARY KEY,
    PositionName VARCHAR(100)
);

-- Таблица "Comments"
CREATE TABLE Comments (
    CommentID INTEGER PRIMARY KEY,
    CommentText TEXT
);

-- Таблица "Measurements"
CREATE TABLE Measurements (
    MeasurementID INTEGER PRIMARY KEY,
    UserID INTEGER,
    ArmPositionID INTEGER,
    BodyPositionID INTEGER,
    CommentID INTEGER,
    Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES Users(UserID),
    FOREIGN KEY (ArmPositionID) REFERENCES ArmPositions(ArmPositionID),
    FOREIGN KEY (BodyPositionID) REFERENCES BodyPositions(BodyPositionID),
    FOREIGN KEY (CommentID) REFERENCES Comments(CommentID)
);

-- Таблица "MeasureDetails"
CREATE TABLE MeasureDetails (
    MeasureDetailID INTEGER PRIMARY KEY,
    MeasurementID INTEGER,
    SystolicPressure INTEGER,
    DiastolicPressure INTEGER,
    Pulse INTEGER,
    FOREIGN KEY (MeasurementID) REFERENCES Measurements(MeasurementID)
);
