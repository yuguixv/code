CREATE DATABASE lab1;
USE lab1

//1、
CREATE TABLE Book (
    ID CHAR(8) PRIMARY KEY,
    name VARCHAR(10) NOT NULL,
    author VARCHAR(10),
    price FLOAT,
    status INT DEFAULT 0,
    times INT DEFAULT 0
)

CREATE TABLE Reader (
    ID CHAR(8) PRIMARY KEY,
    name VARCHAR(10),
    age INT,
    address VARCHAR(20)
)

CREATE TABLE Borrow (
    book_ID CHAR(8),
    Reader_ID CHAR(8),
    BorroW_Data DATE,
    Return_Data DATE,
    PRIMARY KEY (book_ID, Reader_ID),
    FOREIGN KEY (book_ID) REFERENCES Book(ID),
    FOREIGN KEY (Reader_ID) REFERENCES Reader(ID)
)

//插入数据(待做todo)



//2、
SELECT ID, name, author
FROM Book

SELECT R.ID, R.name, B.ID, B.name
FROM Reader R
JOIN Borrow B ON R.ID = B.Reader_ID
WHERE B.Return_Date IS NULL

SELECT ID, name
FROM Reader
WHERE ID NOT IN (SELECT Reader_ID FROM Borrow)

SELECT name, price
FROM Book
WHERE author = 'Ullman' OR author = 'Tanenbaum'

SELECT ID, name, times
FROM Book
WHERE times > 10

SELECT R.name, R.ID
FROM Reader R
JOIN Borrow B ON R.ID = B.Reader_ID
WHERE B.book_ID NOT IN (SELECT book_ID FROM Borrow WHERE Reader_ID = '李林')

SELECT B.ID, B.name, MAX(BW.borrow_data) AS last_borrow_date
FROM Book B
JOIN Borrow BW ON B.ID = BW.book_ID
WHERE BW.Reader_ID LIKE '%MySQL%'
GROUP BY B.ID, B.name

SELECT R.ID, R.name, COUNT(*) AS borrow_times 
FROM Reader R 
JOIN Borrow B ON R.ID = B.Reader_ID 
WHERE YEAR(B.Borrow_Date) = 2025 
GROUP BY R.ID, R.name 
ORDER BY borrow_times DESC 
LIMIT 10;

CREATE VIEW Reader_Borrow AS
SELECT R.ID AS Reader_ID, R.name AS Reader_name, B.ID AS Book_ID, B.name AS Book_name, BW.Borrow_Date
FROM Reader R
JOIN Borrow BW ON R.ID = BW.Reader_ID
JOIN Book B ON BW.book_ID = B.ID;

SELECT Reader_ID, COUNT(DISTINCT Book_ID) AS books_count
FROM Reader_Borrow
WHERE  Borrow_Data >= DATE_SUB(CURDATE(), INTERVAL 1 YEAR)
GROUP BY Reader_ID;


//3、
DELIMITER //
CREATE PROCEDURE SUPERID (IN OLD_ID CHAR(8), IN NEW_ID CHAR(8))
BEGIN
    IF OLD_ID LIKE '00%' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Cannot modify a Super ID';
    ELSEIF NEW_ID LIKE '00%' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Cannot change an ID into a Super ID';
    ELSE
        SET FOREIGN_KEY_CHECKS = 0;
        UPDATE Book SET ID = NEW_ID WHERE ID = OLD_ID;
        UPDATE Borrow SET book_ID = NEW_ID WHERE book_ID = OLD_ID;
        SET FOREIGN_KEY_CHECKS = 1;
    END IF;
END //
DELIMITER ;


//4、
DELIMITER //
CREATE PROCEDURE RETURN_BATCH (IN I_Reader_ID CHAR(8), OUT RETURN_COUNT INT)
BEGIN
    DECLARE ALL_RETURN_COUNT INT DEFAULT 0;
    SELECT COUNT(*) INTO ALL_RETURN_COUNT
    FROM Borrow
    WHERE Reader_ID = I_Reader_ID AND Return_Data IS NULL;
    
    IF ALL_RETURN_COUNT = 0 THEN
        SELECT 'No books to return' AS Message;
        SET RETURN_COUNT = 0;
    ELSE
        UPDATE Book B
        JOIN Borrow BW ON B.ID = BW.book_id
        SET B.status = 0
        WHERE B.Resder_ID = I_Reader_ID AND BW.Return_Data IS NULL;

        UPDATE Borrow
        SET Return_Date = CURDATE()
        WHERE Reader_ID = I_Reader_ID AND Return_Data IS NULL;

        SET RETURN_COUNT = ALL_RETURN_COUNT;
    END IF; 
END //
DELIMITER ;


//5、
DELIMITER //
DROP TRIGGER IF EXISTS borrow_Book;
CREATE TRIGGER borrow_Book AFTER INSERT ON Borrow FOR EACH ROW
BEGIN
    UPDATE Book SET status = 1, times = times + 1 WHERE ID = NEW.book_ID;
END //
DELIMITER ;

DELIMITER //
DROP TRIGGER IF EXISTS return_book;
CREATE TRIGGER return_Book AFTER UPDATE ON Borrow FOR EACH ROW
BEGIN
    IF OLD.Return_Date IS NULL AND NEW.Return_Date IS NOT NULL THEN
        UPDATE Book SET status = 0 WHERE ID = NEW.book_ID;
    END IF;
END //
DELIMITER ;


//6、
DELIMITER //
DROP TRIGGER IF EXISTS check_borrow_insert;
CREATE TRIGGER check_borrow_insert BEFORE INSERT ON Borrow FOR EACH ROW
BEGIN
    DECLARE same_book_count INT;

    IF NEW.Borrow_Date > CURTIME() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Borrow date cannot be later than the current time';
    END IF;

    IF NEW.Return_Date IS NOT NULL AND NEW.Return_Date < NEW.Borrow_Date THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Return date cannot be earlier than borrow date';
    END IF;

    SELECT COUNT(*) INTO same_book_count
    FROM Borrow
    WHERE book_ID = NEW.book_ID AND Reader_ID = NEW_Reader_ID AND Return_Date IS NULL;

    IF same_book_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: This reader has already borrowed this book and has not returned it yet';
    END IF;
END //
DELIMITER ;

DELIMITER //
DROP TRIGGER IF EXISTS check_borrow_update;
CREATE TRIGGER check_borrow_update BEFORE UPDATE ON Borrow FOR EACH ROW
BEGIN
    IF NEW.Borrow_Date > CURTIME() THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Borrow date cannot be later than the current time';
    END IF;

    IF NEW.Return_Date IS NOT NULL AND NEW.Return_Date < NEW.Borrow_Date THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: Return date cannot be earlier than borrow date';
    END IF;

    SELECT COUNT(*) INTO same_book_count
    FROM Borrow
    WHERE book_ID = NEW.book_ID AND Reader_ID = NEW_Reader_ID AND Return_Date IS NULL;

    IF same_book_count > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Error: This reader has already borrowed this book and has not returned it yet';
    END IF;
END //
DELIMITER ;



