# Journalisering af indkomne anmodninger om refusion gruppe 2

This RPA process is made for Folkeregisteret in Aarhus Municipality.

The process reads emails from Outlook and journalize them in KMD Nova.
Both systems are accessed using apis.

The robot made for [OpenOrchestrator](https://github.com/itk-dev-rpa/OpenOrchestrator).

The robot expects an input string in the following json format:

```json
{
  "receivers": [
    ""
  ]
}
```

- **Receivers**: A list of emails to send the status reports to.
