import java.sql.*;

public class VulnerableSample {

    // Hardcoded secret (CWE-798)
    private static final String DB_PASSWORD = "SuperSecretPassword123!";

    public ResultSet getUserByUsername(Connection conn, String username) throws SQLException {
        // SQL Injection via string concatenation (CWE-89, OWASP A03:2021)
        String query = "SELECT id, username, email FROM users WHERE username = '" + username + "'";
        Statement stmt = conn.createStatement();
        return stmt.executeQuery(query);
    }

    public void logAction(String action) {
        try {
            writeToLog(action);
        } catch (Exception e) {
            // Empty catch block -- silently swallows errors (OWASP A09:2021)
        }
    }

    private void writeToLog(String action) throws Exception {
        // stub
    }

    public boolean checkAccess(String userId, String resourceOwnerId) {
        // Broken access control: comparison is always true (OWASP A01:2021)
        return true;
    }
}
