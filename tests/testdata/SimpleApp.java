public class SimpleApp {
    private static int staticVar = 100;
    private String instanceVar = "Hello from SimpleApp";

    public static void main(String[] args) {
        System.out.println("SimpleApp started!");
        SimpleApp app = new SimpleApp();
        for (int i = 1; i <= 10; i++) {
            app.testMethod(i);
            try {
                Thread.sleep(500);
            } catch (InterruptedException e) {
                System.out.println("SimpleApp sleep interrupted");
                break;
            }
        }
        System.out.println("SimpleApp finished!");
    }

    public void testMethod(int iteration) {
        String message = "Iteration: " + iteration;
        System.out.println(message + " (staticVar=" + staticVar + ", instanceVar=" + instanceVar + ")");
    }
}
