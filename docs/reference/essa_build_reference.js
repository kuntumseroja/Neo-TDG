// Build essa_analysis.docx — Knowledge Transfer document for IT Operations
const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  AlignmentType, LevelFormat, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, Footer, Header, PageBreak, ImageRun
} = require('docx');

// ---------- helpers ----------
const border = { style: BorderStyle.SINGLE, size: 1, color: "BFBFBF" };
const borders = { top: border, bottom: border, left: border, right: border };

const h1 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text: t })],
});
const h2 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text: t })],
});
const h3 = (t) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text: t })],
});
const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 120 },
  children: [new TextRun({ text, ...opts })],
});
const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun(text)],
});
const bulletBold = (title, rest) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun({ text: title, bold: true }), new TextRun(rest)],
});
const numbered = (text) => new Paragraph({
  numbering: { reference: "numbers", level: 0 },
  children: [new TextRun(text)],
});
const code = (text) => new Paragraph({
  spacing: { before: 60, after: 120 },
  shading: { fill: "F2F2F2", type: ShadingType.CLEAR },
  children: [new TextRun({ text, font: "Consolas", size: 18 })],
});
const callout = (label, text, color = "0F6FC6") => new Paragraph({
  spacing: { before: 120, after: 120 },
  shading: { fill: "EAF3FB", type: ShadingType.CLEAR },
  children: [
    new TextRun({ text: `${label}:  `, bold: true, color }),
    new TextRun({ text }),
  ]
});

const cell = (text, opts = {}) => new TableCell({
  borders,
  width: { size: opts.width, type: WidthType.DXA },
  shading: opts.fill ? { fill: opts.fill, type: ShadingType.CLEAR } : undefined,
  margins: { top: 80, bottom: 80, left: 120, right: 120 },
  children: [
    new Paragraph({ children: [new TextRun({ text, bold: !!opts.bold, size: 20, color: opts.color })] })
  ],
});

const table = (header, rows, widths, headerFill = "0F6FC6") => {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: header.map((h, i) => cell(h, { width: widths[i], bold: true, fill: headerFill, color: "FFFFFF" }))
      }),
      ...rows.map((r, ri) => new TableRow({
        children: r.map((val, i) => cell(val, {
          width: widths[i],
          fill: ri % 2 === 0 ? "F7F9FC" : undefined,
        }))
      }))
    ]
  });
};

// ---------- document body ----------
const sections = [];

// -------- Cover --------
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 2200, after: 200 },
  children: [new TextRun({ text: "ESSA", bold: true, size: 84, color: "0F6FC6" })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: "Knowledge Transfer Document", bold: true, size: 40 })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 120 },
  children: [new TextRun({ text: "for IT Operations & L3 Developers", bold: true, size: 32, color: "555555" })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 600 },
  children: [new TextRun({ text: "C# / .NET Framework 4.8 — OPC UA Industrial Data Gateway", italics: true, size: 22 })]
}));

sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 80 },
  children: [new TextRun({ text: "Document Type: ", bold: true }), new TextRun("Technical KT / Runbook")]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 80 },
  children: [new TextRun({ text: "Audience: ", bold: true }),
             new TextRun("IT Operations (L1/L2 Application Support, SRE/DevOps, Windows/IIS admins) and L3 Developers (code owners, on-call engineers taking code-level incidents)")]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 80 },
  children: [new TextRun({ text: "Status: ", bold: true }), new TextRun("Draft v1.0")]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 2000 },
  children: [new TextRun({ text: "Last updated: ", bold: true }), new TextRun("April 2026")]
}));
sections.push(new Paragraph({ children: [new PageBreak()] }));

// -------- Document control --------
sections.push(h1("Document Control"));
sections.push(table(
  ["Field", "Value"],
  [
    ["Document title", "ESSA — Knowledge Transfer for IT Operations"],
    ["Version", "1.0"],
    ["Purpose", "Enable the IT Operations team (and new developers) to install, operate, monitor and troubleshoot the ESSA application without prior knowledge of the codebase."],
    ["Intended readers", "L1/L2 application support, Windows/IIS admins, DevOps engineers, on-call responders, AND L3 developers who own code-level escalations and feature work."],
    ["Prerequisite knowledge", "Basic Windows Server / IIS administration, HTTP/REST concepts, Visual Studio 2022, and willingness to read C# code. No OPC UA background required — see the glossary."],
    ["Out of scope", "Designing the industrial network, choosing PLC vendors, provisioning the OPC UA server itself."],
    ["Owners (fill in)", "Application Owner: ______  •  Tech Lead: ______  •  Operations Lead: ______"],
    ["Review cadence", "Review every 6 months or when a major component (OPC UA server, .NET runtime) changes."],
  ],
  [2400, 7360]
));

sections.push(h2("Revision History"));
sections.push(table(
  ["Version", "Date", "Author", "Summary of changes"],
  [
    ["1.0", "2026-04-24", "Handover team", "Initial KT document produced from source-code walkthrough of essa.sln."],
  ],
  [1400, 1800, 2400, 4160]
));

sections.push(new Paragraph({ children: [new PageBreak()] }));

// -------- Table of contents (static list) --------
sections.push(h1("Contents"));
[
  "1. Executive Summary (for managers and new staff)",
  "2. System Context & Business Purpose",
  "3. Solution Layout — the five projects",
  "4. End-to-End Data Flow",
  "5. Technology Stack & Dependencies",
  "6. Configuration Reference",
  "7. Environments & Deployment Topology",
  "8. Build, Package & Release Procedure",
  "9. Installation & First-Time Setup",
  "10. Day-to-Day Operations Runbook",
  "11. Monitoring, Logging & Alerting",
  "12. Security & Compliance Notes",
  "13. Backup, Restore & Disaster Recovery",
  "14. Common Errors & Troubleshooting Matrix",
  "15. Frequently Asked Questions (FAQ)",
  "16. Recommendations to Improve",
  "17. Developer Deep-Dive (L3 Support)",
  "18. Handover Checklist",
  "19. Glossary for New Team Members",
  "20. Contacts & Escalation",
].forEach(line => sections.push(new Paragraph({
  spacing: { after: 40 },
  children: [new TextRun({ text: line, size: 22 })]
})));
sections.push(new Paragraph({ children: [new PageBreak()] }));

// =========================================================
// 1. Executive summary
// =========================================================
sections.push(h1("1. Executive Summary"));
sections.push(p(
  "ESSA is a C# / .NET Framework 4.8 application that acts as a gateway between an OPC UA industrial server " +
  "(used for SCADA, PLCs, sensors) and consumer-facing interfaces (REST API, legacy SOAP web service, console tool). " +
  "It connects to an OPC UA server over opc.tcp://, browses its tag tree, and reads both current and historical " +
  "time-series values, returning them as JSON over HTTP."
));
sections.push(p(
  "In one sentence: ESSA translates the 'factory floor' (OPC UA) into 'web language' (JSON/HTTP) so dashboards, " +
  "reporting and analytics systems can consume plant data without knowing OPC UA."
));
sections.push(callout("Why this matters for Ops",
  "If ESSA is down, any downstream dashboard or report that depends on plant tags will stop updating. Treat it as a " +
  "Tier-2 integration service: not safety-critical, but important for operational visibility."
));

// =========================================================
// 2. System context & business purpose
// =========================================================
sections.push(h1("2. System Context & Business Purpose"));
sections.push(p("ESSA sits between three worlds, as shown in Figure 2.1:"));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 80 },
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync('/sessions/confident-admiring-bohr/mnt/outputs/analysis/context_diagram.png'),
    transformation: { width: 620, height: 282 },
    altText: {
      title: "ESSA system context diagram",
      description: "System context diagram showing Plant/OPC UA Server connecting to ESSA WebApi via opc.tcp, and ESSA WebApi connecting to BI/Dashboards/Integrations via HTTPS/JSON. ESSA WebService (SOAP) sits below WebApi as an optional side-channel.",
      name: "EssaContextDiagram"
    }
  })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({ text: "Figure 2.1 — ESSA System Context", italics: true, size: 18, color: "666666" })]
}));
sections.push(p(
  "Upstream it talks OPC UA (TCP, port typically 53530 for Prosys Simulation Server, 4840 for production servers). " +
  "Downstream it talks HTTP/JSON over whichever port IIS is configured for (80/443 in production)."
));

sections.push(h2("2.1 Who uses it"));
sections.push(bulletBold("Data consumers (downstream): ", "reporting tools, Power BI / Grafana dashboards, historian loaders, any internal service that needs plant values."));
sections.push(bulletBold("Developers: ", "use ConsoleApp1 to test connectivity and tag browsing during development and troubleshooting."));
sections.push(bulletBold("IT Operations (you): ", "install, patch, monitor, restart, and handle incidents on the Windows server hosting IIS and the ESSA deployment."));

// =========================================================
// 3. Solution layout
// =========================================================
sections.push(h1("3. Solution Layout — the Five Projects"));
sections.push(p("The Visual Studio solution (essa.sln) contains five projects:"));
sections.push(table(
  ["Project", "Type", "Purpose for Ops"],
  [
    ["Opc.Ua", "Class Library (.NET 4.8)", "Core library — wraps the OPC UA client, defines the tag model and read services. All other projects depend on this. No direct deployment artefact; built into WebApi/bin and ConsoleApp1/bin."],
    ["ConsoleApp1", "Console Application", "Developer/Ops troubleshooting tool. Use it on the server to verify connectivity to the OPC UA server and list available tags without going through IIS."],
    ["WebApi", "ASP.NET MVC 5 + Web API 2", "The main deployable artefact. Hosted in IIS. Exposes REST endpoints /opc-ua-api/history-raw-data and /opc-ua-api/current-raw-data."],
    ["WebService", "Legacy ASMX (SOAP)", "Legacy placeholder — currently only has a HelloWorld method. Optional deployment."],
    ["HistoricalAccess Client", "External OPC UA sample project", "Referenced from ../opc_ua_sample_code/... for reference only. Not deployed."],
  ],
  [2200, 2200, 5360]
));

sections.push(h2("3.1 Internal module map"));
sections.push(p("Figure 3.1 shows which projects reference the Opc.Ua class library and which NuGet packages each depends on. Red dashed lines mark tech-debt links (e.g., WebService currently has no reference to Opc.Ua)."));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 80 },
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync('/sessions/confident-admiring-bohr/mnt/outputs/analysis/module_diagram.png'),
    transformation: { width: 620, height: 310 },
    altText: {
      title: "ESSA module dependency diagram",
      description: "Module dependency diagram showing ConsoleApp1, WebApi, and WebService projects, with ConsoleApp1 and WebApi referencing the Opc.Ua class library. Opc.Ua depends on OPCFoundation.NetStandard.Opc.Ua.* packages, Newtonsoft.Json, AutoMapper, BouncyCastle. WebApi additionally depends on Ninject. WebService currently has no reference to Opc.Ua (marked as tech debt).",
      name: "EssaModuleDiagram"
    }
  })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({ text: "Figure 3.1 — ESSA Internal Module Dependencies", italics: true, size: 18, color: "666666" })]
}));

sections.push(h2("3.2 Key files by project"));
sections.push(h3("Opc.Ua (library)"));
sections.push(bulletBold("ServerConnector.cs — ", "creates an OPC UA Session; handles endpoint selection, keep-alive and reconnection; auto-accepts untrusted certificates (see Security)."));
sections.push(bulletBold("Interfaces.cs — ", "IHistoryRawData, ICurrentRawData, IRawDataValue — DI contracts."));
sections.push(bulletBold("ClassRawData.cs — ", "concrete HistoryRawData and CurrentRawData — browse tags, call session.HistoryRead(…), map results."));
sections.push(bulletBold("TagCollection.cs — ", "Tag, TagHistoryRawData, TagCurrentRawData model classes."));
sections.push(bulletBold("DataValue.cs — ", "RawDataValue DTO returned over JSON."));
sections.push(bulletBold("AutoMapper.cs — ", "MapperConfig.Initialize() — DataValue → RawDataValue mappings."));
sections.push(bulletBold("AppSetting.cs — ", "static OPCUA_TCP_CONNECTION_ADDRESS field populated at startup."));

sections.push(h3("WebApi (deployable)"));
sections.push(bulletBold("Global.asax.cs — ", "Application_Start registers areas, WebApi/MVC routes, filters, bundles and calls AppSetting.Initialize()."));
sections.push(bulletBold("App_Start/NinjectWebCommon.cs — ", "Ninject DI container: binds IHistoryRawData→HistoryRawData and ICurrentRawData→CurrentRawData."));
sections.push(bulletBold("App_Start/WebApiConfig.cs — ", "attribute routing + default api/{controller}/{id} route."));
sections.push(bulletBold("Controllers/OpcController.cs — ", "the real endpoints: BulkHistoryRawData and CurrentRawData."));
sections.push(bulletBold("Controllers/HomeController.cs — ", "MVC home page + /Home/HelloWorld health-check JSON."));
sections.push(bulletBold("Controllers/ValuesController.cs — ", "scaffolded, unused."));
sections.push(bulletBold("Models/ReadRawCriteriaDto.cs — ", "request-body DTOs."));
sections.push(bulletBold("Web.config — ", "holds OPCUA_TCP_CONNECTION_ADDRESS and all binding redirects."));
sections.push(bulletBold("Dockerfile — ", "packages the app into a Windows Server Core container (mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2019)."));

sections.push(h3("ConsoleApp1 (support tool)"));
sections.push(bullet("Program.cs — three routines: WriteTagChildNodes, WriteSingleTagHistoryRawDataValues, WriteMultipleTagHistoryRawDataValues (the last two are commented out in Main)."));
sections.push(bullet("Contains a local Connector class that duplicates ServerConnector (technical debt — see Recommendations)."));

sections.push(h3("WebService (legacy)"));
sections.push(bullet("WS_OPC_UA.asmx(.cs) — a single WebMethod returning 'Hello World'. Currently no real function."));

// =========================================================
// 4. Data flow
// =========================================================
sections.push(h1("4. End-to-End Data Flow"));
sections.push(p("The sequence diagram below shows what happens when a downstream consumer calls POST /opc-ua-api/history-raw-data. Solid arrows are synchronous calls; dashed arrows are return values; numbered badges on the left of each arrow match the narrative steps after the diagram."));

// Sequence diagram as an image
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 120 },
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync('/sessions/confident-admiring-bohr/mnt/outputs/analysis/sequence_diagram.png'),
    // fit to ~6.5 inches wide on US Letter with 1" margins
    transformation: { width: 620, height: 560 },
    altText: {
      title: "ESSA sequence diagram",
      description: "Sequence diagram showing the flow of a POST /opc-ua-api/history-raw-data request through HTTP Client, ASP.NET Web API, Ninject, OpcController, HistoryRawData, ServerConnector, and OPC UA Server, including the per-item loop over criteria.",
      name: "EssaSequenceDiagram"
    }
  })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({ text: "Figure 4.1 — End-to-end sequence for POST /opc-ua-api/history-raw-data", italics: true, size: 18, color: "666666" })]
}));

sections.push(h2("4.1 Narrative — step by step"));
sections.push(numbered("HTTP client sends the JSON body [ { StartDateTime, EndDateTime, TagId } ] to POST /opc-ua-api/history-raw-data."));
sections.push(numbered("ASP.NET deserialises the body into ReadRawCriteriaCollectionDto."));
sections.push(numbered("Ninject resolves OpcController and injects HistoryRawData (IHistoryRawData) and CurrentRawData (ICurrentRawData)."));
sections.push(numbered("OpcController.BulkHistoryRawData(dto) runs — it iterates the criteria collection."));
sections.push(numbered("For each item the controller calls _iHistoryRawData.Read(start, end, tagId), which internally:"));
sections.push(bullet("5a. ServerConnector.CreateSession(serverUrl, useSecurity) — opens a new OPC UA session."));
sections.push(bullet("5b. ServerConnector does the opc.tcp:// handshake and selects an endpoint from the server."));
sections.push(bullet("5c. HistoryRawData calls session.Browse(ObjectsFolder) to locate the tag that matches the TagId."));
sections.push(bullet("5d. session.HistoryRead(ReadRawModifiedDetails) is issued with the time window."));
sections.push(bullet("5e. AutoMapper converts each OPC UA DataValue into the lightweight RawDataValue DTO."));
sections.push(bullet("5f. HistoryRawData yield-returns TagHistoryRawData (Name, NodeId, Id, RawDataValues[]) back to the controller."));
sections.push(numbered("Controller returns Ok(tags) — the Web API runtime serialises the list to JSON and sends 200 OK to the client."));

sections.push(callout("Operational note",
  "Every call currently opens a new OPC UA session. Under load this is expensive and can exhaust sessions on the " +
  "OPC UA server. See Recommendations §16 — session reuse."
));

// =========================================================
// 5. Tech stack & dependencies
// =========================================================
sections.push(h1("5. Technology Stack & Dependencies"));
sections.push(table(
  ["Layer", "Technology", "Version", "Why it's here"],
  [
    ["Runtime", ".NET Framework", "4.8", "Required because ASMX and classic ASP.NET don't run on .NET 6/7/8."],
    ["Language", "C#", "7.3 / 8.0", "Default for net48 projects."],
    ["Industrial protocol", "OPC UA", "1.5.374.54", "OPCFoundation.NetStandard.Opc.Ua.* — official OPC Foundation stack."],
    ["Web API", "ASP.NET Web API 2", "5.2.9", "HTTP/JSON endpoints."],
    ["MVC (views/home)", "ASP.NET MVC", "5.2.9", "Razor views, bundling."],
    ["Legacy SOAP", "ASP.NET ASMX", "System.Web.Services", "WS_OPC_UA.asmx."],
    ["DI container", "Ninject", "3.3.x", "Wires IHistoryRawData / ICurrentRawData into OpcController."],
    ["JSON", "Newtonsoft.Json", "13.0.3", "Serialization of Tag / RawDataValue."],
    ["Object mapping", "AutoMapper", "10.1.1", "DataValue → RawDataValue, Tag → TagHistoryRawData."],
    ["Crypto", "BouncyCastle.Cryptography", "2.3.1", "Required by the OPC UA stack for certificate handling."],
    ["Packaging", "packages.config (classic NuGet)", "-", "Pre-PackageReference style; packages restored into /packages."],
    ["Containers", "Windows Server Core", "ltsc2019", "Dockerfile base image for WebApi and WebService."],
    ["Front-end (Home view)", "Bootstrap 5.2.3, jQuery 3.4.1, Modernizr", "-", "Default MVC template — not really used."],
  ],
  [1900, 2600, 1500, 3360]
));

sections.push(h2("5.1 Key NuGet Packages"));
sections.push(table(
  ["Package", "Where used", "Role"],
  [
    ["OPCFoundation.NetStandard.Opc.Ua.Core", "Opc.Ua, WebApi, ConsoleApp1", "Core types (NodeId, DataValue, ExtensionObject, StatusCode)."],
    ["OPCFoundation.NetStandard.Opc.Ua.Client", "Opc.Ua, ConsoleApp1", "Session, Browse, HistoryRead, KeepAlive."],
    ["OPCFoundation.NetStandard.Opc.Ua.Client.ComplexTypes", "Opc.Ua, ConsoleApp1", "ComplexTypeSystem loader for user-defined structures."],
    ["OPCFoundation.NetStandard.Opc.Ua.Configuration", "Opc.Ua, ConsoleApp1", "ApplicationConfiguration, endpoint selection."],
    ["AutoMapper 10.1.1", "Opc.Ua", "Maps OPC UA DataValue → RawDataValue DTO."],
    ["Newtonsoft.Json 13.0.3", "All", "JSON (de)serialization."],
    ["Ninject 3.3.x", "WebApi", "Constructor injection for controllers."],
    ["Microsoft.AspNet.WebApi 5.2.9", "WebApi", "The Web API 2 runtime."],
    ["Microsoft.AspNet.Mvc 5.2.9", "WebApi", "Razor views (HomeController)."],
    ["BouncyCastle.Cryptography 2.3.1", "All", "Certificate/crypto primitives."],
  ],
  [3400, 2800, 3160]
));

// =========================================================
// 6. Configuration
// =========================================================
sections.push(h1("6. Configuration Reference"));

sections.push(h2("6.1 Settings that Ops will change"));
sections.push(table(
  ["Setting", "File", "Example value", "Effect"],
  [
    ["OPCUA_TCP_CONNECTION_ADDRESS", "WebApi/Web.config (<appSettings>)", "opc.tcp://plc-server:4840/UA/Server", "The OPC UA endpoint ESSA connects to. Change per environment."],
    ["useSecurity", "Hard-coded in ClassRawData.cs / ConsoleApp1.Program.cs", "false", "Whether OPC UA connection is signed/encrypted. False is DEV-only."],
    ["TimeZone (console only)", "ConsoleApp1/Program.cs", "SE Asia Standard Time", "Used to convert timestamps when printing to console."],
    ["compilation debug", "WebApi/Web.config", "true", "Must be FALSE for production IIS deployment."],
    ["Binding redirects", "WebApi/Web.config <runtime>", "see file", "Required — do not remove; the OPC UA stack pulls mixed assembly versions."],
  ],
  [2200, 2400, 2600, 2560]
));

sections.push(h2("6.2 Current configured value (as seen in repo)"));
sections.push(code(
    "<!-- WebApi/Web.config -->\n" +
    "<appSettings>\n" +
    "  <add key=\"OPCUA_TCP_CONNECTION_ADDRESS\"\n" +
    "       value=\"opc.tcp://DESKTOP-AMCOF2V:53530/OPCUA/SimulationServer\" />\n" +
    "</appSettings>"
));
sections.push(callout("Action for Ops",
  "DESKTOP-AMCOF2V is a developer workstation hostname and must NOT be deployed. Before any UAT/PROD release, " +
  "replace this with the environment-specific OPC UA endpoint via a Web.config transform or an environment variable.",
  "C00000"
));

// =========================================================
// 7. Environments & deployment topology
// =========================================================
sections.push(h1("7. Environments & Deployment Topology"));

sections.push(h2("7.1 Suggested environments"));
sections.push(table(
  ["Env", "Hostname (example)", "OPC UA endpoint", "Purpose"],
  [
    ["DEV", "essa-dev.contoso.local", "opc.tcp://sim-server:53530/OPCUA/SimulationServer", "Developer integration, points to Prosys simulator."],
    ["UAT", "essa-uat.contoso.local", "opc.tcp://plc-uat:4840/UA/Server", "Business testing with representative tag set."],
    ["PROD", "essa.contoso.com", "opc.tcp://plc-prod:4840/UA/Server", "Live plant data; HTTPS only."],
  ],
  [1200, 2800, 3400, 2360]
));

sections.push(h2("7.2 Runtime topology"));
sections.push(p("Figure 7.1 shows the deployment topology across the consumer network, the Windows Server host, and the Plant / OT VLAN, plus the host-level concerns the Operations team owns."));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { before: 120, after: 80 },
  children: [new ImageRun({
    type: "png",
    data: fs.readFileSync('/sessions/confident-admiring-bohr/mnt/outputs/analysis/topology_diagram.png'),
    transformation: { width: 620, height: 413 },
    altText: {
      title: "ESSA runtime deployment topology",
      description: "Runtime deployment topology showing three zones: Consumer network (BI/Dashboards and optional load balancer), Windows Server hosting IIS 10 with AppPool Essa and two sites (Site:Essa at / and Site:Essa-WS at /ws), and the Plant/OT VLAN hosting the OPC UA Server. Additional Host/Ops concerns include Windows Updates, AV/EDR, Event Log and IIS Logs, Certificates, and Backup of IIS config plus Web.config.",
      name: "EssaTopologyDiagram"
    }
  })]
}));
sections.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({ text: "Figure 7.1 — ESSA Runtime Deployment Topology", italics: true, size: 18, color: "666666" })]
}));

sections.push(h2("7.3 Host requirements"));
sections.push(bulletBold("OS: ", "Windows Server 2019 or 2022 (Standard/Datacenter)."));
sections.push(bulletBold("Web server: ", "IIS 10+, ASP.NET 4.8 role, WebSocket + WebDeploy optional."));
sections.push(bulletBold(".NET runtime: ", ".NET Framework 4.8 Developer Pack on build server; .NET 4.8 runtime on target."));
sections.push(bulletBold("Network: ", "outbound access to the OPC UA server port (typically 4840 or 53530). Inbound on 443 from the client network."));
sections.push(bulletBold("Certificates: ", "IIS SSL cert for the public URL; OPC UA client cert in the Windows / OPC Foundation trust store once Security is enabled."));
sections.push(bulletBold("Resource sizing (minimum): ", "2 vCPU, 4 GB RAM, 20 GB disk. Scale up if response payloads become large (history windows)."));

// =========================================================
// 8. Build, package, release
// =========================================================
sections.push(h1("8. Build, Package & Release Procedure"));
sections.push(h2("8.1 Build prerequisites"));
sections.push(bullet("Visual Studio 2022 17.5+ OR MSBuild 17 + NuGet 6.x on a build agent."));
sections.push(bullet(".NET Framework 4.8 Developer Pack."));
sections.push(bullet("Internet access (or an internal NuGet mirror) so OPCFoundation / Ninject / AutoMapper packages restore."));

sections.push(h2("8.2 Build steps (manual)"));
sections.push(numbered("Open essa.sln in Visual Studio 2022."));
sections.push(numbered("Tools → NuGet Package Manager → Restore."));
sections.push(numbered("Build → Rebuild Solution in Release configuration."));
sections.push(numbered("Right-click WebApi → Publish → File system → produces a publish folder."));

sections.push(h2("8.3 CI/CD (recommended)"));
sections.push(bullet("Pipeline: nuget restore → msbuild /p:Configuration=Release /p:DeployOnBuild=true /p:PublishProfile=FileSystem → artifact zip."));
sections.push(bullet("Release: Web Deploy to the target IIS, or Docker build/push for Windows container hosts."));
sections.push(bullet("Apply Web.config transforms per environment (Web.Release.config, Web.<Env>.config)."));

sections.push(h2("8.4 Docker packaging"));
sections.push(code(
    "docker build -t essa-webapi:1.0 -f WebApi/Dockerfile WebApi/\n" +
    "docker run -d -p 8080:80 --name essa essa-webapi:1.0"
));
sections.push(callout("Note",
  "The image is based on Windows Server Core (~4 GB). You need a Docker host running Windows containers — Linux " +
  "nodes cannot run it unless the app is migrated to .NET 8."));

// =========================================================
// 9. Installation / first-time setup
// =========================================================
sections.push(h1("9. Installation & First-Time Setup"));
sections.push(h2("9.1 Fresh server install (IIS)"));
sections.push(numbered("Install Windows roles: Web Server (IIS), Application Development → ASP.NET 4.8, ISAPI, Static Content."));
sections.push(numbered("Install .NET Framework 4.8 runtime if missing."));
sections.push(numbered("Copy publish folder to C:\\inetpub\\wwwroot\\essa (or any preferred path)."));
sections.push(numbered("Create an AppPool 'Essa' — .NET CLR v4.0, Integrated pipeline, Identity = a dedicated service account that has read/write on %ProgramData%\\OPC Foundation\\CertificateStores."));
sections.push(numbered("Create a Site 'Essa', bind HTTPS:443 with a valid cert, point to the publish folder, assign the Essa AppPool."));
sections.push(numbered("Edit Web.config → set OPCUA_TCP_CONNECTION_ADDRESS and set compilation debug=\"false\"."));
sections.push(numbered("Test in a browser: https://<host>/Home/HelloWorld should return {\"x\":\"hello\",\"y\":\"world\"}."));
sections.push(numbered("Test a real endpoint with Postman (see §10.4)."));

sections.push(h2("9.2 Deploying ConsoleApp1 to the server"));
sections.push(p("Keep ConsoleApp1 as a support tool under C:\\Tools\\essa-console\\. It doesn't need IIS."));
sections.push(numbered("Copy ConsoleApp1\\bin\\Release\\ to the server."));
sections.push(numbered("Edit ConsoleApp1.exe.config (or App.config at source) to point to the right server URL."));
sections.push(numbered("Run ConsoleApp1.exe from cmd/PowerShell — the list of tags is printed."));

// =========================================================
// 10. Day-to-day runbook
// =========================================================
sections.push(h1("10. Day-to-Day Operations Runbook"));

sections.push(h2("10.1 Start / stop / restart"));
sections.push(code(
    ":: IIS — restart the AppPool (fastest, no full IIS restart)\n" +
    "C:\\Windows\\System32\\inetsrv\\appcmd.exe recycle apppool /apppool.name:\"Essa\"\n\n" +
    ":: Stop / start the site\n" +
    "C:\\Windows\\System32\\inetsrv\\appcmd.exe stop  site /site.name:\"Essa\"\n" +
    "C:\\Windows\\System32\\inetsrv\\appcmd.exe start site /site.name:\"Essa\""
));

sections.push(h2("10.2 Health check"));
sections.push(bulletBold("Liveness URL: ", "GET https://<host>/Home/HelloWorld — should return {\"x\":\"hello\",\"y\":\"world\"}. If this fails, IIS/AppPool/ASP.NET is down."));
sections.push(bulletBold("Upstream check: ", "Run ConsoleApp1.exe on the server — it must print the Simulation child tags. If it hangs or errors out, the OPC UA server is unreachable or rejecting the connection."));
sections.push(bulletBold("End-to-end check: ", "POST a real payload (see §10.4)."));

sections.push(h2("10.3 Routine checks (suggested schedule)"));
sections.push(table(
  ["Frequency", "Check", "Action if failing"],
  [
    ["Every 5 min (automated)", "HTTP probe on /Home/HelloWorld", "Page on-call if > 3 consecutive failures."],
    ["Hourly (automated)", "Synthetic POST of a known tag", "Create incident ticket; confirm OPC UA server health."],
    ["Daily", "Review IIS logs for 5xx spikes", "Open investigation if 5xx > 1% of traffic."],
    ["Weekly", "Check disk, memory, AppPool worker memory", "Recycle AppPool if w3wp.exe is approaching 2 GB."],
    ["Monthly", "Patch Windows Server + .NET Framework", "Schedule change window + smoke test after patches."],
    ["Quarterly", "Review security certs, rotate service-account password", "Follow cert renewal SOP."],
  ],
  [2000, 3700, 4060]
));

sections.push(h2("10.4 Smoke-test requests"));
sections.push(code(
    "POST https://<host>/opc-ua-api/current-raw-data\n" +
    "Content-Type: application/json\n\n" +
    "[ { \"TagId\": \"Simulation/Counter1\" } ]"
));
sections.push(code(
    "POST https://<host>/opc-ua-api/history-raw-data\n" +
    "Content-Type: application/json\n\n" +
    "[ { \"StartDateTime\": \"2026-04-24T00:00:00Z\",\n" +
    "    \"EndDateTime\":   \"2026-04-24T00:05:00Z\",\n" +
    "    \"TagId\":         \"Simulation/Counter1\" } ]"
));

sections.push(h2("10.5 Change / release process"));
sections.push(numbered("Raise a Change Request referencing this KT."));
sections.push(numbered("Deploy to DEV → UAT → PROD with the same artifact."));
sections.push(numbered("After each deploy: hit /Home/HelloWorld and a current-raw-data smoke test."));
sections.push(numbered("Rollback = re-deploy the previous build (keep last 3 versions retained on disk)."));

// =========================================================
// 11. Monitoring, logging, alerting
// =========================================================
sections.push(h1("11. Monitoring, Logging & Alerting"));
sections.push(h2("11.1 Logs today"));
sections.push(bullet("IIS logs: %SystemDrive%\\inetpub\\logs\\LogFiles\\W3SVC<id>\\ — HTTP access logs."));
sections.push(bullet("Windows Event Log: Application + System — for AppPool crashes / ASP.NET errors."));
sections.push(bullet("OPC UA stack log: written under %ProgramData%\\OPC Foundation\\... once enabled. Currently the code calls Utils.LogError(...) only in one place, so operational visibility is LOW."));

sections.push(h2("11.2 Recommended monitoring"));
sections.push(bullet("APM agent (Application Insights / Dynatrace / New Relic) installed on the AppPool — gives request rate, latency, failures."));
sections.push(bullet("Synthetic transaction every 1–5 minutes hitting /Home/HelloWorld and one /opc-ua-api/current-raw-data."));
sections.push(bullet("Windows performance counters: w3wp Memory, %% CPU, IIS Current Requests, .NET CLR Exceptions."));
sections.push(bullet("Disk free, AppPool identity login failures, Windows updates pending."));

sections.push(h2("11.3 Recommended alerts"));
sections.push(table(
  ["Metric", "Threshold", "Severity"],
  [
    ["HTTP 5xx rate", "> 2% for 5 min", "P2"],
    ["Liveness probe fails", "3 consecutive", "P1"],
    ["w3wp private bytes", "> 1.5 GB for 10 min", "P3 (recycle)"],
    ["OPC UA connection failures in app log", "> 5 in 5 min", "P2"],
    ["Disk free (C:)", "< 10%", "P2"],
    ["Certificate expiry (IIS or OPC UA)", "< 30 days", "P3"],
  ],
  [3800, 3200, 2760]
));

// =========================================================
// 12. Security
// =========================================================
sections.push(h1("12. Security & Compliance Notes"));
sections.push(h2("12.1 Current posture"));
sections.push(bulletBold("OPC UA: ", "useSecurity is hard-coded to false. Certificates are auto-accepted. This is lab-grade only."));
sections.push(bulletBold("REST API: ", "there is no authentication or authorisation on the endpoints — any network-reachable client can post queries."));
sections.push(bulletBold("Transport: ", "HTTPS is a deployment concern (IIS binding); the code itself does not enforce it."));
sections.push(bulletBold("Secrets: ", "no secrets are stored today (no DB, no API keys). The OPC UA URL is in Web.config."));

sections.push(h2("12.2 Required hardening before PROD"));
sections.push(bullet("Put HTTPS-only bindings in IIS; add HSTS response headers."));
sections.push(bullet("Add authentication — Windows Authentication for intranet or OAuth2 / JWT for external clients. Reject anonymous POSTs."));
sections.push(bullet("Enable OPC UA security (Basic256Sha256, SignAndEncrypt) and replace AutoAcceptUntrustedCertificates with a trusted cert list."));
sections.push(bullet("Run the AppPool under a dedicated least-privilege service account."));
sections.push(bullet("Restrict outbound network to the OPC UA server host/port only (firewall rule)."));
sections.push(bullet("Enable audit logging: every successful and failed request."));

// =========================================================
// 13. Backup & DR
// =========================================================
sections.push(h1("13. Backup, Restore & Disaster Recovery"));
sections.push(p(
  "ESSA itself is stateless — it stores no data. Backup strategy therefore focuses on the deployment artefact " +
  "and the configuration, not on application data."
));
sections.push(bulletBold("What to back up: ", "the publish folder (IIS site content), Web.config per environment, the IIS site/AppPool export (appcmd list site /config /xml > essa.xml), any certificate .pfx files."));
sections.push(bulletBold("RPO / RTO target (suggested): ", "RPO 0 (no state), RTO < 1 hour — redeploy from last artifact."));
sections.push(bulletBold("DR playbook: ", "stand up a fresh Windows host, run §9 Installation, restore IIS configuration from XML, re-bind the certificate, verify health endpoints."));

// =========================================================
// 14. Errors & Troubleshooting
// =========================================================
sections.push(h1("14. Common Errors & Troubleshooting Matrix"));
sections.push(table(
  ["Error / Symptom", "Likely cause", "Resolution"],
  [
    ["BadNotConnected / 'Could not connect to server'",
     "Wrong URL, OPC UA server not running, firewall blocks port.",
     "Verify server is running; ping host; telnet port; check OPCUA_TCP_CONNECTION_ADDRESS. Use ConsoleApp1.exe to isolate."],
    ["BadSecurityChecksFailed",
     "Certificate mismatch or security policy rejected.",
     "In DEV keep useSecurity=false. In PROD import the server cert into pki\\trusted; configure SecurityPolicy Basic256Sha256."],
    ["BadIdentityTokenRejected",
     "Server requires username/password or cert identity.",
     "Set Connector.UserIdentity = new UserIdentity(\"user\",\"pass\") before CreateSession; raise a code change."],
    ["TypeInitializationException / binding redirect errors",
     "Two different versions of Newtonsoft.Json / System.Memory requested.",
     "Keep <bindingRedirect> entries; do not downgrade Newtonsoft.Json below 13.0.3."],
    ["ConfigurationErrorsException: 'Required permissions cannot be acquired.'",
     "AppPool identity can't access OPC UA PKI directory.",
     "Grant service account rwx on %ProgramData%\\OPC Foundation\\CertificateStores\\..."],
    ["NullReferenceException at results[0].HistoryData.Body",
     "Tag has no history in that window; Body is null.",
     "Check the tag is history-enabled; caller should widen the window. Guard is partially in place already."],
    ["Deadlock / request hangs forever",
     "Session.Create(...).Result inside ASP.NET sync context.",
     "Short-term: recycle AppPool. Long-term: migrate controller chain to async (see Recommendations)."],
    ["HTTP 500 — 'No parameterless constructor defined for this object'",
     "Ninject isn't wired; controller can't be instantiated.",
     "Confirm NinjectWebCommon.Start ran; confirm the WebActivatorEx attribute is intact; check all bindings."],
    ["Docker build fails with 'failed to compute cache key'",
     "Running docker build on Linux without Windows container mode.",
     "Switch Docker Desktop to Windows containers, or migrate app to .NET 8."],
    ["SerializationException / cyclic reference in JSON",
     "Serializing raw DataValue instead of RawDataValue DTO.",
     "Always return the POCOs (RawDataValue / TagHistoryRawData). AutoMapper is there for this."],
    ["w3wp.exe memory keeps growing",
     "One-session-per-request pattern leaking under load.",
     "Temporary: schedule AppPool recycle every N hours. Permanent: session caching (§16)."],
    ["/Home/HelloWorld works but /opc-ua-api/* returns 404",
     "Attribute routing not picked up (config.MapHttpAttributeRoutes() missed).",
     "Check WebApiConfig.Register ran; redeploy."],
    ["Clients see timeouts > 30s",
     "HistoryRead range too wide / NumValuesPerNode too large (99,999,999 today).",
     "Narrow the time window in the client; add server paging (see Recommendations)."],
  ],
  [3300, 2900, 3160]
));

// =========================================================
// 15. FAQ
// =========================================================
sections.push(h1("15. Frequently Asked Questions (FAQ)"));
const faqs = [
  ["Q1. What is OPC UA?",
   "OPC UA (Unified Architecture) is a machine-to-machine protocol used in industrial automation. It lets you read tags (like 'Tank1.Level') from PLCs, DCS, SCADA and historians in a standard way. Think of it as 'SQL for factories'."],
  ["Q2. What is a 'tag' / 'NodeId'?",
   "A tag is a named data point on the server (Temperature, Counter1...). Each one has a NodeId such as ns=3;i=1002 where ns is a namespace index and i is a numeric identifier. The code also builds a friendly Id like 'Simulation/Counter1'."],
  ["Q3. Why does the app target .NET Framework 4.8 instead of .NET 8?",
   "Because it uses ASMX (System.Web.Services) and classic ASP.NET MVC, which are Windows-only and not ported to modern .NET. The OPC UA stack itself works fine on .NET 8 — only the web hosting keeps you on 4.8."],
  ["Q4. What does Ninject do here?",
   "It's a Dependency Injection (DI) container. It reads NinjectWebCommon.RegisterServices and, whenever ASP.NET needs an OpcController, it automatically supplies new HistoryRawData() and new CurrentRawData() for its constructor parameters."],
  ["Q5. What is AutoMapper mapping, exactly?",
   "It turns the heavy OPC UA DataValue (nested types, server-specific fields) into a simple POCO RawDataValue with five fields. The Web API returns the POCO so JSON consumers get a clean shape."],
  ["Q6. What is the difference between 'current' and 'historical' raw data?",
   "'Current' asks the server for the value right now (actually a 1-second window from now onward). 'Historical' asks the server's historian for everything between StartDateTime and EndDateTime — this only works if the OPC UA server has Historical Access (HA) enabled."],
  ["Q7. Why are there two identical-looking connectors (Connector in ConsoleApp1 and ServerConnector in Opc.Ua)?",
   "Connector was the original prototype; ServerConnector is the library version. Technical debt — they should be merged."],
  ["Q8. Why is useSecurity = false?",
   "Because the code currently targets a local Simulation Server on the developer's machine. You MUST turn this on (and configure certificates) for real deployments."],
  ["Q9. How do I add a new endpoint, e.g. 'write a value to a tag'?",
   "Add a Write method on IHistoryRawData (or a new IWriteData), implement it via session.Write(...), register it in NinjectWebCommon, and add a POST action on OpcController."],
  ["Q10. Can I deploy this in Docker?",
   "Yes — the Dockerfiles build on mcr.microsoft.com/dotnet/framework/aspnet:4.8-windowsservercore-ltsc2019. Only a Windows Docker host (or Windows nodes in Kubernetes) can run it. For Linux containers you have to migrate to .NET 8 first."],
  ["Q11. Which OPC UA server works out-of-the-box with this code?",
   "Prosys OPC UA Simulation Server (free, Windows). Its 'Simulation' folder contains numeric tags with history enabled."],
  ["Q12. What does 'SE Asia Standard Time' in Program.cs mean?",
   "It converts the server's UTC timestamps to UTC+7 (Jakarta/Bangkok). Hard-coded in ConsoleApp1 — a real deployment should return ISO-8601 UTC."],
  ["Q13. Who owns this application?",
   "Fill in the Owners row in Document Control. Typically: the Plant Data Integration / OT-IT team owns the application; IT Operations owns the Windows hosts and network."],
  ["Q14. Can I run it without the plant network?",
   "Yes — install Prosys OPC UA Simulation Server on localhost and point OPCUA_TCP_CONNECTION_ADDRESS to it. This is how DEV works."],
  ["Q15. Where do request logs go?",
   "IIS access logs by default (inetpub\\logs). There is currently no structured application-level log — see §16 for the recommendation to add one."],
];
faqs.forEach(([q, a]) => {
  sections.push(new Paragraph({
    spacing: { before: 120, after: 60 },
    children: [new TextRun({ text: q, bold: true, color: "0F6FC6" })]
  }));
  sections.push(p(a));
});

// =========================================================
// 16. Recommendations
// =========================================================
sections.push(h1("16. Recommendations to Improve"));

sections.push(h2("16.1 Architecture & code quality"));
sections.push(bulletBold("Unify the connectors. ", "ConsoleApp1 has its own Connector class that is almost identical to Opc.Ua.ServerConnector. Delete it and reuse the library class."));
sections.push(bulletBold("Async all the way. ", "ServerConnector.CreateSession calls .Result on an async Session.Create. This can deadlock in ASP.NET classic. Make it async and await it (IHttpActionResult supports Task<IHttpActionResult>)."));
sections.push(bulletBold("Reuse the Session. ", "Every call currently creates a fresh Session. Cache one Session per server URL and re-use it — faster and easier on the OPC UA server."));
sections.push(bulletBold("Replace static AppSetting. ", "Mutable public static fields are hard to test. Use IOptions<T> / constructor injection."));
sections.push(bulletBold("Handle exceptions. ", "Several catch blocks are empty. Add Serilog/NLog and log Exception.Message + StackTrace with a correlation id."));
sections.push(bulletBold("Migrate to PackageReference. ", "Classic packages.config is deprecated; the /packages folder also bloats the repo."));
sections.push(bulletBold("Consider upgrading to .NET 8. ", "The OPC UA stack runs on .NET Standard 2.0 and works on .NET 8. This unlocks Linux containers and better perf."));

sections.push(h2("16.2 API & data model"));
sections.push(bulletBold("Version the API. ", "/opc-ua-api/... is unversioned — add /v1/ for forward safety."));
sections.push(bulletBold("Validate inputs. ", "StartDateTime < EndDateTime, reasonable range, non-empty TagId; return 400 with a problem detail."));
sections.push(bulletBold("Cap NumValuesPerNode. ", "99999999 can OOM the OPC UA server. Use continuation points + paging."));
sections.push(bulletBold("Strongly-typed RawDataValue. ", "Value/StatusCode/Timestamps are declared as object — use concrete types."));
sections.push(bulletBold("Add GET /opc-ua-api/tags. ", "So clients can discover what TagIds exist without out-of-band docs."));

sections.push(h2("16.3 Security"));
sections.push(bulletBold("Do not auto-accept certificates. ", "Import the server cert into the client trust list once and reject everything else."));
sections.push(bulletBold("Enable OPC UA SignAndEncrypt. ", "Basic256Sha256 at minimum."));
sections.push(bulletBold("Authenticate the REST API. ", "OAuth2/JWT or at least per-client API keys."));
sections.push(bulletBold("Never commit DESKTOP-AMCOF2V. ", "Use Web.config transforms or environment variables."));

sections.push(h2("16.4 Operations"));
sections.push(bulletBold("Real /health endpoint. ", "Return 200 only if an OPC UA session can be opened. Today /HelloWorld only proves IIS is up."));
sections.push(bulletBold("Structured logging + correlation ID. ", "Propagate a request id through the OPC UA call for faster RCA."));
sections.push(bulletBold("Metrics. ", "Expose Prometheus / App Insights counters: sessions_created_total, history_read_duration_seconds, opcua_reconnect_total."));
sections.push(bulletBold("Remove or implement WebService. ", "It is currently dead code."));

// =========================================================
// 17. Developer Deep-Dive (L3 Support)
// =========================================================
sections.push(h1("17. Developer Deep-Dive (L3 Support)"));
sections.push(p(
  "This section is for L3 engineers — the people who get the ticket after Ops has exhausted the runbook. It assumes " +
  "you can read C#, open the solution in Visual Studio, attach a debugger to w3wp.exe, and raise a code change."
));

sections.push(h2("17.1 How to set up a local developer loop"));
sections.push(numbered("Install Visual Studio 2022 17.5+ with workloads: ASP.NET and web development, .NET desktop development."));
sections.push(numbered("Install .NET Framework 4.8 Developer Pack."));
sections.push(numbered("Install Prosys OPC UA Simulation Server (or any OPC UA server with a 'Simulation' folder with history-enabled tags)."));
sections.push(numbered("Clone the repo, open essa.sln, right-click solution → Restore NuGet Packages, Rebuild."));
sections.push(numbered("Set WebApi as the Startup Project and press F5 — it launches under IIS Express."));
sections.push(numbered("Alternative: set ConsoleApp1 as startup and F5 — fastest feedback loop for OPC UA experiments (no IIS involved)."));

sections.push(h2("17.2 Key classes and their responsibilities"));
sections.push(table(
  ["Class", "File", "What L3 needs to know"],
  [
    ["ServerConnector", "Opc.Ua/ServerConnector.cs", "Creates and owns the OPC UA Session. CreateSession() calls .Result on an async — potential deadlock point under ASP.NET sync context. Session_KeepAlive has empty branches; reconnect logic is effectively a stub."],
    ["HistoryRawData", "Opc.Ua/ClassRawData.cs", "IHistoryRawData implementation. Browses tags twice (two nested Browse calls) every request, then HistoryRead with NumValuesPerNode = 99,999,999. Returns IEnumerable<TagHistoryRawData> via yield."],
    ["CurrentRawData", "Opc.Ua/ClassRawData.cs", "ICurrentRawData implementation. Same browse logic; uses a 1-second HistoryRead window starting 'now' as a proxy for 'current value'. Not a true OPC UA Read — if a tag has no history, it returns nothing."],
    ["MapperConfig", "Opc.Ua/AutoMapper.cs", "One-shot static AutoMapper configuration. Maps OPC UA DataValue → RawDataValue (Value, ValueDataType, StatusCode, SourceTimestamp, ServerTimestamp)."],
    ["NinjectWebCommon", "WebApi/App_Start/NinjectWebCommon.cs", "DI wiring. Any new interface you add must also be bound here or the controller will throw 'No parameterless constructor'."],
    ["OpcController", "WebApi/Controllers/OpcController.cs", "The REST surface. Two POST endpoints; synchronous; no validation; returns Ok(tags). New endpoints go here."],
    ["AppSetting (WebApi)", "WebApi/AppSetting.cs", "Reads Web.config at startup and copies OPCUA_TCP_CONNECTION_ADDRESS into Opc.Ua.AppSetting. Tight coupling — prefer IOptions<T> when refactoring."],
  ],
  [2000, 2600, 5160]
));

sections.push(h2("17.3 Extension points — how to add a feature"));
sections.push(h3("A. Add a new REST endpoint"));
sections.push(numbered("Declare a new method on an existing interface (e.g., IWriteData.Write(tagId, value)) in Opc.Ua/Interfaces.cs."));
sections.push(numbered("Implement it in Opc.Ua/ClassRawData.cs using session.Write(...) (OPC UA WriteValueCollection)."));
sections.push(numbered("Bind it in NinjectWebCommon.RegisterServices → kernel.Bind<IWriteData>().To<WriteData>();"));
sections.push(numbered("Add a DTO in WebApi/Models and a POST action on OpcController with a [Route(\"opc-ua-api/...\")] attribute."));
sections.push(numbered("Build, run, smoke-test with Postman."));

sections.push(h3("B. Expose live value subscriptions"));
sections.push(bullet("Use OPC UA Subscription + MonitoredItems. Adds long-running callbacks — pair with SignalR to push to clients."));
sections.push(bullet("Warning: the current Ninject scope is per-request. Subscriptions need singletons — adjust the binding (.InSingletonScope())."));

sections.push(h3("C. Add a new tag browse endpoint"));
sections.push(bullet("Expose the existing GetVariableTags(session) enumerator through a new interface (ITagBrowser.BrowseAll())."));
sections.push(bullet("This is the easiest useful win — today there is no way for clients to discover TagIds."));

sections.push(h2("17.4 Debugging procedures"));
sections.push(h3("Local: attach debugger"));
sections.push(numbered("In Visual Studio: Debug → Attach to Process → select iisexpress.exe (local) or w3wp.exe (server, requires remote debug tools)."));
sections.push(numbered("Set a breakpoint in OpcController.BulkHistoryRawData and in HistoryRawData.Read."));
sections.push(numbered("Fire a POST with Postman; step through to see which line throws/blocks."));

sections.push(h3("On the server: enabling detailed OPC UA stack logs"));
sections.push(bullet("Add Opc.Ua.Utils.SetTraceMask(Opc.Ua.Utils.TraceMasks.All) at start-up (temporary diagnostic)."));
sections.push(bullet("Log file lands in %ProgramData%\\OPC Foundation\\Logs\\Opc.Ua.Client.log (subject to write-permission on that folder)."));
sections.push(bullet("Tail it during the failing request: Get-Content Opc.Ua.Client.log -Wait in PowerShell."));

sections.push(h3("On the server: production dump"));
sections.push(bullet("Use procdump (Sysinternals) to capture a memory dump when w3wp hits a deadlock: procdump -ma -w w3wp.exe."));
sections.push(bullet("Open the dump in Visual Studio → Debug Managed Memory → look for lots of threads blocked on Task.Result / SemaphoreSlim (classic async-over-sync)."));

sections.push(h2("17.5 Known code-level risks (read before fixing)"));
sections.push(bulletBold("Async-over-sync deadlock risk (HIGH). ", "ServerConnector.CreateSession calls Connect(...).Result synchronously. Any caller running under a single-threaded SynchronizationContext (classic ASP.NET) can deadlock. See Recommendation 16.1."));
sections.push(bulletBold("Session-per-request (MEDIUM). ", "HistoryRawData.Read and CurrentRawData.Read each create a fresh Session and never Close() it explicitly. Under load this leaks sockets on both sides."));
sections.push(bulletBold("Unbounded history window (MEDIUM). ", "NumValuesPerNode = 99,999,999 lets a malicious/careless caller pull huge result sets. Add a server-side cap (e.g., 10,000) and continuation-point paging."));
sections.push(bulletBold("Empty catch blocks (MEDIUM). ", "ServerConnector.Session_KeepAlive and CertificateValidator_CertificateValidation swallow exceptions silently. Replace with structured logging."));
sections.push(bulletBold("Duplicate Connector in ConsoleApp1 (LOW). ", "Technical debt — collapse into ServerConnector."));
sections.push(bulletBold("Hard-coded timezone (LOW). ", "Program.cs uses 'SE Asia Standard Time' — only affects the dev console but will bite if someone reuses that code path in a service."));
sections.push(bulletBold("No input validation (MEDIUM/SECURITY). ", "OpcController does not validate DTOs. A null TagId causes a NullReference inside GetVariableTags."));

sections.push(h2("17.6 L3 triage cheat-sheet"));
sections.push(table(
  ["Symptom", "First diagnostics (5 min)", "Likely root cause"],
  [
    ["All requests time out", "Take a w3wp mini-dump; check Threads for Result/Wait/SemaphoreSlim.", "Async-over-sync deadlock in Connect()."],
    ["Empty arrays returned", "Hit /current-raw-data with a tag you KNOW has history.", "Tag has no HA; or Browse filter misses it; or server cert changed and session rejected."],
    ["Intermittent 500s", "Check Event Viewer — Application log for .NET runtime errors.", "NullReferenceException in ClassRawData when HistoryData.Body is null for some tags."],
    ["Works in DEV, fails in PROD with BadSecurityChecksFailed", "Confirm OPC UA cert path and trust list.", "useSecurity flipped to true, but trust store not seeded."],
    ["Slow response > 5s", "Open an APM trace — is the time in session.HistoryRead or in Browse?", "Session creation overhead; session-per-request pattern."],
    ["Controller 500 with ActivationException (Ninject)", "Check NinjectWebCommon.RegisterServices binding list.", "New interface added but not bound in DI."],
    ["Cannot bind cert on IIS after server move", "certlm.msc → check private key access for AppPool identity.", "AppPool identity lost private-key ACL after a cert re-import."],
  ],
  [2500, 3500, 3760]
));

sections.push(h2("17.7 Suggested test harness for L3"));
sections.push(bullet("xUnit project targeting net48 referencing Opc.Ua."));
sections.push(bullet("Add an interface around ServerConnector (ISessionFactory) so HistoryRawData can be unit-tested with a fake session (Moq)."));
sections.push(bullet("Integration tests run against Prosys Simulation Server in CI (Windows agent)."));
sections.push(bullet("Add a health-contract test that hits /Home/HelloWorld and one /opc-ua-api/current-raw-data — fail the build if either regresses."));

sections.push(h2("17.8 Where to read more"));
sections.push(bullet("OPC Foundation .NET Standard reference: https://reference.opcfoundation.org/"));
sections.push(bullet("OPC UA .NET samples (the 'HistoricalAccess Client' that essa.sln references)."));
sections.push(bullet("Ninject docs: https://github.com/ninject/Ninject/wiki"));
sections.push(bullet("AutoMapper 10 docs: https://docs.automapper.org/en/stable/"));
sections.push(bullet("Classic ASP.NET Web API 2 attribute routing: https://learn.microsoft.com/en-us/aspnet/web-api/overview/web-api-routing-and-actions/attribute-routing-in-web-api-2"));

// =========================================================
// 18. Handover checklist
// =========================================================
sections.push(h1("18. Handover Checklist"));
sections.push(p("Use this checklist during KT sessions. Tick each item when the Operations team has seen it demonstrated and can reproduce it."));
sections.push(table(
  ["✓", "Item", "Notes"],
  [
    ["☐", "Overview walk-through", "Solution layout, 5 projects, what each does."],
    ["☐", "Data flow demo (Postman)", "current-raw-data + history-raw-data against DEV."],
    ["☐", "Source code repository access", "Ops team has at least read access + clone instructions."],
    ["☐", "CI/CD pipeline access", "Can view build history and trigger a re-deploy."],
    ["☐", "IIS administration", "Start/stop site + AppPool recycle demonstrated."],
    ["☐", "ConsoleApp1 on the server", "Ops can run it for troubleshooting."],
    ["☐", "Config change process", "How to change OPCUA_TCP_CONNECTION_ADDRESS safely."],
    ["☐", "Log locations", "IIS + Event Log; where future application logs will land."],
    ["☐", "Monitoring dashboard link", "APM / synthetic probes visible to the Ops team."],
    ["☐", "Alert routing", "Pager duty / email DL configured; escalation tested."],
    ["☐", "Backup & DR drill", "Fresh install from last artifact completed in < RTO."],
    ["☐", "Security posture reviewed", "HTTPS, AppPool identity, OPC UA security, cert expiry."],
    ["☐", "Known issues list", "Async-deadlock, session-per-call, empty catch blocks."],
    ["☐", "Contacts & escalation", "Owners named in Document Control."],
    ["☐", "L3 dev environment set up", "Clone, restore, build, F5 demonstrated (Visual Studio + Prosys simulator)."],
    ["☐", "L3 can attach debugger", "Attach to iisexpress.exe locally and w3wp.exe on a non-prod server."],
    ["☐", "L3 can reproduce prod-class issues", "Replay a known incident (e.g., BadSecurityChecksFailed, empty result)."],
    ["☐", "L3 has repo write access + CI/CD permissions", "Can merge to main and trigger a Release pipeline."],
    ["☐", "L3 walked through 17.3 extension recipes", "Adding endpoint, adding binding in Ninject, adding DTO."],
    ["☐", "L3 reviewed 17.5 known risks", "Async-over-sync, session-per-request, unbounded window, empty catch."],
  ],
  [600, 3200, 5960]
));

// =========================================================
// 19. Glossary
// =========================================================
sections.push(h1("19. Glossary for New Team Members"));
sections.push(bulletBold("OPC UA — ", "Open Platform Communications Unified Architecture: an industrial protocol for reading/writing data from plant equipment."));
sections.push(bulletBold("Session — ", "a live connection to the OPC UA server; like a database connection."));
sections.push(bulletBold("NodeId — ", "unique id of a data point on the server (ns=3;i=1002)."));
sections.push(bulletBold("HistoryRead — ", "an OPC UA call to read historical values for a node, bounded by start/end time."));
sections.push(bulletBold("ExtensionObject — ", "OPC UA's container for complex structured data (we wrap ReadRawModifiedDetails in one)."));
sections.push(bulletBold("Ninject Kernel — ", "the DI registry object that returns instances of services."));
sections.push(bulletBold("DTO — ", "Data Transfer Object. A flat class used only to move data between layers / serialise to JSON."));
sections.push(bulletBold("MVC 5 / Web API 2 — ", "classic ASP.NET stacks. MVC for HTML views, Web API for HTTP/JSON endpoints."));
sections.push(bulletBold("ASMX — ", "legacy SOAP web service format (WS_OPC_UA.asmx). Replaced by WCF and then by gRPC/REST."));
sections.push(bulletBold("AppPool — ", "IIS isolation boundary; each AppPool is its own w3wp.exe process."));
sections.push(bulletBold("PKI / Trust list — ", "files on disk under %ProgramData%\\OPC Foundation\\... that decide which certificates are accepted."));
sections.push(bulletBold("Prosys Simulation Server — ", "a free OPC UA server commonly used in DEV; exposes a 'Simulation' folder of synthetic tags with history."));

// =========================================================
// 20. Contacts
// =========================================================
sections.push(h1("20. Contacts & Escalation"));
sections.push(p("Replace the placeholders below with real names before the document is published."));
sections.push(table(
  ["Role", "Name", "Email / Phone", "When to contact"],
  [
    ["Application Owner", "______", "______", "Business-level decisions, scope changes."],
    ["Tech Lead", "______", "______", "Architecture and code changes."],
    ["On-call Application Support (L2)", "______ rota", "______", "Incidents affecting the REST API or IIS."],
    ["L3 Developer / Engineering on-call", "______ rota", "______", "Code-level bugs, deadlocks, memory dumps, extension work, production hot-fixes."],
    ["OT / Plant Integration", "______", "______", "OPC UA server / tag definitions / network."],
    ["Windows / IIS Admin", "______", "______", "Host, patching, certificates, AppPool."],
    ["Security / Compliance", "______", "______", "Cert issuance, audit, penetration tests."],
  ],
  [2600, 2000, 2600, 2560]
));

sections.push(new Paragraph({ spacing: { before: 300 }, children: [new TextRun({ text: "— End of Document —", italics: true, color: "888888" })], alignment: AlignmentType.CENTER }));

// ---------- document ----------
const doc = new Document({
  creator: "ESSA KT — Handover Team",
  title: "ESSA — Knowledge Transfer for IT Operations",
  description: "Technical KT / Runbook for the ESSA OPC UA gateway solution",
  styles: {
    default: { document: { run: { font: "Calibri", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 34, bold: true, font: "Calibri", color: "0F6FC6" },
        paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Calibri", color: "1F4E79" },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Calibri", color: "333333" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      },
      { reference: "numbers",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } }
        }]
      },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "ESSA — KT for IT Operations & L3 Developers", size: 18, color: "888888", italics: true })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Confidential — Internal KT  •  Page ", size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 18, color: "888888" }),
            new TextRun({ text: " / ", size: 18, color: "888888" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18, color: "888888" }),
          ]
        })]
      })
    },
    children: sections
  }]
});

Packer.toBuffer(doc).then(buf => {
  const out = '/sessions/confident-admiring-bohr/mnt/outputs/analysis/essa_analysis.docx';
  fs.writeFileSync(out, buf);
  console.log('wrote', out, buf.length, 'bytes');
});
