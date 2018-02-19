"use strict";

var nodeDict = {};
var rootNodes = [];
var treeFormats = {};
var selectedId = "";

var dataSource = "http://data.bellz.org/data/SFBooks.trln";
var openMarker = "\u2296";
var closedMarker = "\u2295";
var leafMarker = "\u25CB";
loadFile();

function loadFile() {
    // initial data load
    var xhttp = new XMLHttpRequest();
    xhttp.overrideMimeType("application/json");
    xhttp.open("GET", dataSource, true);
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            var fileData = JSON.parse(this.responseText);
            fileData.formats.forEach(function(formatData) {
                var formatName = formatData.formatname;
                treeFormats[formatName] = new NodeFormat(formatData);
            });
            var node;
            fileData.nodes.forEach(function(nodeData) {
                node = new TreeNode(treeFormats[nodeData.format], nodeData);
                nodeDict[node.uId] = node;
            });
            var uId;
            for (uId in nodeDict) {
                nodeDict[uId].assignRefs();
            }
            rootNodes = fileData.properties.topnodes.map(function(id) {
                return nodeDict[id];
            });
            var rootElement = document.getElementById("rootlist");
            rootNodes.forEach(function(rootNode) {
                rootNode.open = true;
                rootNode.outputElement(rootElement);
            });
        }
    }
    xhttp.send(null);
}

function TreeNode(formatRef, fileData) {
    // class to store nodes
    this.formatRef = formatRef;
    this.uId = fileData.uid;
    this.data = fileData.data;
    this.tmpChildRefs = fileData.children;
    this.childList = [];
    this.open = false;
}
TreeNode.prototype.assignRefs = function() {
    // add actual refs to child nodes
    this.childList = this.tmpChildRefs.map(function(id) {
        return nodeDict[id];
    });
    this.tmpChildRefs = [];
}
TreeNode.prototype.outputElement = function(parentElement) {
    // recursively output html tree elements
    var element = document.createElement("li");
    var markerSpan = document.createElement("span");
    var markerText = leafMarker;
    if (this.childList.length > 0) {
        markerText = this.open ? openMarker : closedMarker;
    }
    markerSpan.appendChild(document.createTextNode(markerText));
    markerSpan.className = "marker";
    element.appendChild(markerSpan);
    var textSpan = document.createElement("span");
    textSpan.appendChild(document.createTextNode(this.formatRef.
                                                 formatTitle(this)));
    textSpan.className = "nodetext";
    element.appendChild(textSpan);
    element.setAttribute("id", this.uId);
    parentElement.appendChild(element);
    if (this.open && this.childList.length > 0) this.openChildren(element);
}
TreeNode.prototype.openChildren = function(parentElement) {
    // output children of this node
    var listElement = document.createElement("ul");
    parentElement.appendChild(listElement);
    this.childList.forEach(function(child) {
        child.outputElement(listElement);
    });
}
TreeNode.prototype.toggleOpen = function() {
    // toggle this node's opened/closed state
    if (this.childList.length == 0) return;
    this.open = !this.open;
    var element = document.getElementById(this.uId);
    if (this.open) {
        element.childNodes[0].innerHTML = openMarker;
        this.openChildren(element);
    } else {
        element.childNodes[0].innerHTML = closedMarker;
        var elementList = element.childNodes;
        for (var i = 0; i < elementList.length; i++) {
            if (elementList[i].tagName == "UL") {
                element.removeChild(elementList[i]);
            }
        }
    }
}

function NodeFormat(formatData) {
    // class to store node format data and format output
    this.fieldDict = {};
    formatData.fields.forEach(function(fieldData) {
        this.fieldDict[fieldData.fieldname] = new FieldFormat(fieldData);
    }, this);
    this.titleLine = this.parseLine(formatData.titleline);
    this.outputLines = formatData.outputlines.map(this.parseLine, this);
    this.spaceBetween = valueOrDefault(formatData, "spacebetween", true);
    this.formatHtml = false;
}
NodeFormat.prototype.parseLine = function(text) {
    // parse text with embedded fields, return list of fields and text
    var segments = text.split(/({\*(?:\**|\?|!|&|#)[\w_\-.]+\*})/g);
    return segments.map(this.parseField, this).filter(String);
}
NodeFormat.prototype.parseField = function(text) {
    // parse text field, return field type or plain text if not a field
    var match = /{\*(\**|\?|!|&|#)([\w_\-.]+)\*}/g.exec(text);
    if (match) {
        var modifier = match[1];
        var fieldName = match[2];
        if (modifier == "" && fieldName in this.fieldDict) {
            return this.fieldDict[fieldName];
        }
    }
    return text;
}
NodeFormat.prototype.formatTitle = function(node) {
    // return a string with formatted title data
    var result = this.titleLine.map(function(part) {
        if (typeof part.outputText === "function") {
            return part.outputText(node, true, this.formatHtml);
        }
        return part;
    }, this);
    return result.join("").trim().split("\n", 1)[0];
}
NodeFormat.prototype.formatOutput = function(node) {
    // return a list of formatted text output lines
    var line, numEmptyFields, numFullFields, text, match;
    var result = [];
    this.outputLines.forEach(function(lineData) {
        line = "";
        numEmptyFields = 0;
        numFullFields = 0;
        lineData.forEach(function(part) {
            if (typeof part.outputText === "function") {
                text = part.outputText(node, false, this.formatHtml);
                if (text) {
                    numFullFields += 1;
                } else {
                    numEmptyFields += 1;
                }
                line += text;
            } else {
                if (!this.formatHtml) {
                    part = escapeHtml(part);
                }
                line += part;
            }
        }, this);
        if (numFullFields > 0 || numEmptyFields == 0) {
            result.push(line);
        } else if (this.formatHtml && result.length > 0) {
            match = /.*(<br[ /]*?>|<hr[ /]*?>)$/gi.exec(line);
            if (match) {
                result[result.length - 1] += match[1];
            }
        }
    }, this);
    return result;
}

function FieldFormat(fieldData) {
    // class to store field format data and format field output
    this.name = fieldData.fieldname;
    this.fieldType = fieldData.fieldtype;
    this.format = valueOrDefault(fieldData, "format", "");
    this.prefix = valueOrDefault(fieldData, "prefix", "");
    this.suffix = valueOrDefault(fieldData, "suffix", "");
}
FieldFormat.prototype.outputText = function(node, titleMode, formatHtml) {
    // return formatted output text for this field in this node
    var value = valueOrDefault(node.data, this.name, "");
    if (!value) return "";
    switch (this.fieldType) {
        case "OneLineText":
            value = value.split("<br />", 1)[0];
            break;
        case "SpacedText":
            value = "<pre>" + value + "</pre";
            break;
        case "Number":
            var num = Number(value);
            value = formatNumber(num, this.format);
            break;
    }
    var prefix = this.prefix;
    var suffix = this.suffix;
    if (titleMode) {
        value = removeMarkup(value);
        if (formatHtml) {
            prefix = removeMarkup(prefix);
            suffix = removeMarkup(suffix);
        }
    } else if (!formatHtml) {
        prefix = escapeHtml(prefix);
        suffix = escapeHtml(suffix);
    }
    return prefix + value + suffix;
}

function OutputItem(node, level) {
    // class to store output for a single node
    this.textLines = node.formatRef.formatOutput(node).map(function(line) {
        return line + "<br />";
    });
    this.level = level;
    this.uId = node.uId;
    this.addSpace = node.formatRef.spaceBetween;
}
OutputItem.prototype.addIndent = function(prevLevel, nextLevel) {
    for (var i = 0; i < this.level - prevLevel; i++) {
        this.textLines[0] = "<div>" + this.textLines[0];
    }
    for (var i = 0; i < this.level - nextLevel; i++) {
        this.textLines[this.textLines.length - 1] += "</div>";
    }
}

function OutputGroup() {
    // class to store and modify output lines
    this.itemList = [];
    var parentNode = nodeDict[selectedId];
    if (parentNode) {
        this.itemList.push(new OutputItem(parentNode, 0));
        this.addChildren(parentNode, 0);
        this.addBlanksBetween();
        this.addIndents();
    }
}
OutputGroup.prototype.addChildren = function(node, level) {
    // recursively add output items for descendants
    node.childList.forEach(function(child) {
        this.itemList.push(new OutputItem(child, level + 1));
        this.addChildren(child, level + 1);
    }, this);
}
OutputGroup.prototype.addBlanksBetween = function() {
    // add blank lines between items based on node format
    for (var i = 0; i < this.itemList.length - 1; i++) {
        if (this.itemList[i].addSpace || this.itemList[i + 1].addSpace) {
            var lines = this.itemList[i].textLines;
            lines[lines.length - 1] += "<br />"
        }
    }
}
OutputGroup.prototype.addIndents = function() {
    // add nested <div> elements to define indentations in the output
    var prevLevel = 0;
    var nextLevel;
    for (var i = 0; i < this.itemList.length; i++) {
        if (i + 1 < this.itemList.length) {
            nextLevel = this.itemList[i + 1].level;
        } else {
            nextLevel = 0;
        }
        this.itemList[i].addIndent(prevLevel, nextLevel);
        prevLevel = this.itemList[i].level;
    }
}
OutputGroup.prototype.getText = function() {
    // return a text string for all output
    if (this.itemList.length == 0) return "";
    var lines = [];
    this.itemList.forEach(function(item) {
        lines = lines.concat(item.textLines);
    });
    return lines.join("\n");
}

window.onclick = function(event) {
    // handle mouse clicks for open/close and selection
    if (event.target.tagName == "SPAN") {
        if (event.target.classList.contains("marker")) {
            var uId = event.target.parentElement.getAttribute("id");
            if (uId in nodeDict) {
                nodeDict[uId].toggleOpen();
            }
        } else if (event.target.classList.contains("nodetext")) {
            var uId = event.target.parentElement.getAttribute("id");
            if (uId in nodeDict) {
                var prevId = selectedId;
                selectedId = uId;
                if (prevId) {
                    var prevElem = document.getElementById(prevId);
                    prevElem.childNodes[1].classList.remove("selected");
                }
                event.target.classList.add("selected");
                var outputGroup = new OutputGroup();
                document.getElementById("output").innerHTML =
                         outputGroup.getText();
            }
        }
    }
}

function valueOrDefault(object, name, dflt) {
    // return the value of the named property or the default value
    var value = object[name];
    if (value !== undefined) return value;
    return dflt;
}

function escapeHtml(text) {
    // return the given string with &, <, > escaped
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').
           replace(/>/g, '&gt;');
}

function removeMarkup(text) {
    // return text with all HTML Markup removed and entities unescaped
    return text.replace(/<.*?>/g, "").replace(/&amp;/g, "&").
           replace(/&lt;/g, "<").replace(/&gt/g, ">");
}

function formatNumber(num, format) {
    // return a formttted string for the given number
    var formatParts = format.split(/e/i);
    if (formatParts.length < 2) return formatBasicNumber(num, format);
    format = formatParts[0];
    var expFormat = formatParts[1];
    return num.toString();
}

function formatBasicNumber(num, format) {
    // return a formatted string for the given number without an exponent
    return num.toString();
}
