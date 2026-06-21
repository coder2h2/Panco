const vscode = require('vscode');

class PancoDebugConfigurationProvider {
    resolveDebugConfiguration(folder, config, token) {
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor) {
            const filePath = activeEditor.document.fileName;
            
            // Find or create terminal
            let terminal = vscode.window.terminals.find(t => t.name === "Panco Debugger");
            if (!terminal) {
                terminal = vscode.window.createTerminal("Panco Debugger");
            }
            terminal.show();
            
            // Execute debug command
            terminal.sendText(`delta debug "${filePath}"`);
        } else {
            vscode.window.showErrorMessage("No active file to debug.");
        }
        return undefined; // Prevents VS Code from attempting to spawn a separate DAP adapter
    }
}

function activate(context) {
    const provider = new PancoDebugConfigurationProvider();
    context.subscriptions.push(vscode.debug.registerDebugConfigurationProvider('panco', provider));
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
