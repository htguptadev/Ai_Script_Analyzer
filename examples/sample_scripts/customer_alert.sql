-- Script to alert customers for overdue loans
INPUT CUSTOMER_ID
IF BALANCE > LIMIT THEN
    CALL PENALTY_CALC
    DISPLAY ALERT_MESSAGE
ELSE
    PRINT SAFE_STATUS
END IF
/* Raise error for missing customer */
RAISE ERROR 'Customer not found'
