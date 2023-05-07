//  live_tree_export.js, provides javascript code for a read-only tree view
//  Works with TreeLine, an information storage program
//  Copyright (C) 2023, Douglas W. Bell

//  This is free software; you can redistribute it and/or modify it under the
//  terms of the GNU General Public License, either Version 2 or any later
//  version.  This program is distributed in the hope that it will be useful,
//  but WITTHOUT ANY WARRANTY.  See the included LICENSE file for details.

"use strict";

var spotDict = {};
var rootSpots = [];
var treeFormats = {};
var selectedSpot = null;
var openMarker = "\u2296";
var closedMarker = "\u2295";
var leafMarker = "\u25CB";

function main() {
    if (dataFileName) {
        if (dataFilePath) {
            dataFileName = dataFilePath + "/" + dataFileName;
        }
        loadFile(dataFileName);
    } else {
        loadData(document.getElementById("json").innerHTML);
    }
}

function loadFile(filePath) {
    // initial load from file link
    var xhttp = new XMLHttpRequest();
    xhttp.overrideMimeType("application/json");
    xhttp.open("GET", filePath, true);
    xhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
            loadData(this.responseText);
        }
    }
    xhttp.send(null);
}

function loadData(textData) {
    // initial load from file data
    var fileData = JSON.parse(textData);
    fileData.formats.forEach(function(formatData) {
        var formatName = formatData.formatname;
        treeFormats[formatName] = new NodeFormat(formatData);
    });
    var node, spot;
    fileData.nodes.forEach(function(nodeData) {
        node = new TreeNode(treeFormats[nodeData.format], nodeData);
        spot = new TreeSpot(node, nodeData.uid);
    });
    rootSpots = fileData.properties.topnodes.map(function(id) {
        return spotDict[id];
    });
    rootSpots.forEach(function(rootSpot) {
        rootSpot.nodeRef.assignRefs(null);
    });
    var rootElement = document.getElementById("rootlist");
    rootSpots.forEach(function(rootSpot) {
        if (rootSpot.nodeRef.childList.length > 0) rootSpot.open = true;
        rootSpot.outputElement(rootElement);
    });
}

function TreeSpot(nodeRef, uId) {
    // class to store node positions (unique even for cloned nodes)
    this.nodeRef = nodeRef;
    this.uId = uId;
    this.parentSpot;
    this.open = false;
    spotDict[uId] = this;
    nodeRef.spotRefs.push(this);
}
TreeSpot.prototype.childSpots = function() {
    // return an array of child spots
    return this.nodeRef.childList.map(function(node) {
        return node.matchedSpot(this);
    }, this);
}
TreeSpot.prototype.outputElement = function(parentElement) {
    // recursively output html tree elements
    var node = this.nodeRef;
    var element = document.createElement("li");
    var markerSpan = document.createElement("span");
    var markerText = leafMarker;
    if (node.childList.length > 0) {
        markerText = this.open ? openMarker : closedMarker;
    }
    markerSpan.appendChild(document.createTextNode(markerText));
    markerSpan.className = "marker";
    element.appendChild(markerSpan);
    var textSpan = document.createElement("span");
    textSpan.appendChild(document.createTextNode(node.formatRef.
                                                 formatTitle(this)));
    textSpan.className = "nodetext";
    element.appendChild(textSpan);
    element.setAttribute("id", this.uId);
    parentElement.appendChild(element);
    if (this.open && node.childList.length > 0) this.openChildren(element);
}
TreeSpot.prototype.openChildren = function(parentElement) {
    // output children of this node
    var listElement = document.createElement("ul");
    parentElement.appendChild(listElement);
    this.childSpots().forEach(function(childSpot) {
        childSpot.outputElement(listElement);
    });
}
TreeSpot.prototype.toggleOpen = function() {
    // toggle this spot's opened/closed state
    if (this.nodeRef.childList.length == 0) return;
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
TreeSpot.prototype.openParents = function() {
    // open all parent spots of this spot
    var ancestors = [];
    var spot = this.parentSpot;
    var element;
    while (spot) {
        ancestors.unshift(spot);
        spot = spot.parentSpot;
    }
    ancestors.forEach(function(ancestor) {
        if (!ancestor.open) {
            ancestor.open = true;
            element = document.getElementById(ancestor.uId);
            element.childNodes[0].innerHTML = openMarker;
            ancestor.openChildren(element);
        }
    });
}
TreeSpot.prototype.select = function() {
    // change selection to this
    var prevSpot = selectedSpot;
    selectedSpot = this;
    if (prevSpot) {
        var prevElem = document.getElementById(prevSpot.uId);
        if (prevElem) prevElem.childNodes[1].classList.remove("selected");
    }
    var element = document.getElementById(this.uId);
    element.childNodes[1].classList.add("selected");
    var outputGroup = new OutputGroup();
    document.getElementById("output").innerHTML = outputGroup.getText();
}
TreeSpot.prototype.prevTreeSpot = function() {
    // return the previous open spot in tree order
    var pos, node, sibling;
    if (this.parentSpot) {
        pos = this.parentSpot.nodeRef.childList.indexOf(this.nodeRef);
        if (pos <= 0) return this.parentSpot;
        node = this.parentSpot.nodeRef.childList[pos - 1];
        sibling = node.matchedSpot(this.parentSpot);
    } else {
        pos = rootSpots.indexOf(this);
        if (pos <= 0) return null;
        sibling = rootSpots[pos - 1];
    }
    while (sibling.open) {
        node = sibling.nodeRef.childList[sibling.nodeRef.childList.
                                         length - 1];
        sibling = node.matchedSpot(sibling);
    }
    return sibling;
}
TreeSpot.prototype.nextTreeSpot = function() {
    // return the next open spot in tree order
    if (this.open) {
        return this.nodeRef.childList[0].matchedSpot(this);
    }
    var pos, sibling;
    var ancestor = this;
    while (ancestor.parentSpot) {
        pos = ancestor.parentSpot.nodeRef.childList.indexOf(ancestor.nodeRef);
        sibling = ancestor.parentSpot.nodeRef.childList[pos + 1];
        if (sibling) {
            return sibling.matchedSpot(ancestor.parentSpot);
        }
        ancestor = ancestor.parentSpot;
    }
    pos = rootSpots.indexOf(ancestor);
    sibling = rootSpots[pos + 1];
    if (sibling) return sibling;
    return null;
}

function TreeNode(formatRef, fileData) {
    // class to store nodes
    this.formatRef = formatRef;
    this.data = fileData.data;
    this.tmpChildRefs = fileData.children;
    this.spotRefs = [];
    this.childList = [];
}
TreeNode.prototype.assignRefs = function(parentSpot) {
    // recursively add actual refs to child nodes and parent spots
    var spot = this.spotRefs[0];
    if (spot.parentSpot !== undefined) {  // cloned node
        var id = spot.uId;
        var num = 1;
        do {
            id = id + "_" + num;
            num += 1;
        } while (id in spotDict);
        spot = new TreeSpot(this, id);
    }
    spot.parentSpot = parentSpot;
    this.childList.forEach(function(child) {  // for clones (2nd time thru)
        child.assignRefs(spot);
    });
    var childNode;
    this.tmpChildRefs.forEach(function(childId) {  // for first time thru
        childNode = spotDict[childId].nodeRef;
        this.childList.push(childNode);
        childNode.assignRefs(spot);
    }, this);
    this.tmpChildRefs = [];
}
TreeNode.prototype.matchedSpot = function(parentSpot) {
    // return the spot for this node that matches the given parent spot
    for (var i = 0; i < this.spotRefs.length; i++) {
        if (this.spotRefs[i].parentSpot === parentSpot) {
            return this.spotRefs[i];
        }
    }
    return null;
}

function NodeFormat(formatData) {
    // class to store node format data and format output
    this.fieldDict = {};
    formatData.fields.forEach(function(fieldData) {
        this.fieldDict[fieldData.fieldname] = new FieldFormat(fieldData);
    }, this);
    this.spaceBetween = valueOrDefault(formatData, "spacebetween", true);
    this.formatHtml = valueOrDefault(formatData, "formathtml", false);
    this.outputSeparator = valueOrDefault(formatData, "outputsep", ", ");
    this.siblingPrefix = "";
    this.siblingSuffix = "";
    this.titleLine = this.parseLine(formatData.titleline);
    var lines = formatData.outputlines;
    this.useBullets = valueOrDefault(formatData, "bullets", false);
    if (this.useBullets) {
        this.siblingPrefix = "<ul>";
        this.siblingSuffix = "</ul>";
        if (lines != [""]) {
            lines[0] = "<li>" + lines[0];
            lines[lines.length - 1] += "</li>";
        }
    }
    this.useTables = valueOrDefault(formatData, "tables", false);
    if (this.useTables) {
        lines = lines.filter(String);
        var newLines = [];
        var headings = [];
        var head, firstPart, parts;
        lines.forEach(function(line) {
            head = "";
            firstPart = this.parseLine(line)[0];
            if (typeof firstPart == "string" && firstPart.indexOf(":") >= 0) {
                parts = line.split(":");
                head = parts.shift();
                line = parts.join("");
            }
            newLines.push(line.trim());
            headings.push(head.trim());
        }, this);
        this.siblingPrefix = '<table border="1" cellpadding="3">';
        if (headings.filter(String).length > 0) {
            this.siblingPrefix += "<tr>";
            headings.forEach(function(hd) {
                this.siblingPrefix += "<th>" + hd + "</th>";
            }, this);
            this.siblingPrefix += "</tr>";
        }
        this.siblingSuffix = "</table>";
        lines = newLines.map(function(line) {
            return "<td>" + line + "</td>";
        });
        lines[0] = "<tr>" + lines[0];
        lines[lines.length - 1] += "</tr>";
    }
    this.outputLines = lines.map(this.parseLine, this);
}
NodeFormat.prototype.parseLine = function(text) {
    // parse text with embedded fields, return list of fields and text
    var segments = text.split(/({\*(?:\**|\?|!|&|#)[\w_\-.]+\*})/g);
    return segments.map(this.parseField, this).filter(String);
}
NodeFormat.prototype.parseField = function(text) {
    // parse text field, return field type or plain text if not a field
    var field;
    var match = /{\*(\**|\?|!|&|#)([\w_\-.]+)\*}/g.exec(text);
    if (match) {
        var modifier = match[1];
        var fieldName = match[2];
        if (modifier == "" && fieldName in this.fieldDict) {
            return this.fieldDict[fieldName];
        } else if (modifier.match(/^\*+$/)) {
            field = new FieldFormat({"fieldname": fieldName,
                                     "fieldtype": "AncestorLevel"});
            field.ancestorLevel = modifier.length;
            field.placeholder = true;
            return field;
        } else if (modifier == "?") {
            field = new FieldFormat({"fieldname": fieldName,
                                     "fieldtype": "AnyAncestor"});
            field.placeholder = true;
            return field;
        } else if (modifier == "&") {
            field = new FieldFormat({"fieldname": fieldName,
                                     "fieldtype": "ChildList"});
            field.placeholder = true;
            return field;
        } else if (modifier == "#") {
            match = /[^0-9]+([0-9]+)$/.exec(fieldName);
            if (match && match[1] != "0") {
                field = new FieldFormat({"fieldname": fieldName,
                                         "fieldtype": "DescendantCount"});
                field.descendantLevel = Number(match[1]);
                field.placeholder = true;
                return field;
            }
        } else if (modifier == "!") {
            field = new FieldFormat({"fieldname": fieldName,
                                     "fieldtype": "StaticFileInfo"});
            if (fieldName == "File_Name") {
                field.staticInfo = dataFileName;
            } else if (fieldName == "File_Path") {
                field.staticInfo = dataFilePath;
            }
            field.placeholder = true;
            return field;
        }
    }
    return text;
}
NodeFormat.prototype.formatTitle = function(spot) {
    // return a string with formatted title data
    var result = this.titleLine.map(function(part) {
        if (typeof part.outputText === "function") {
            return part.outputText(spot, true, this.formatHtml);
        }
        return part;
    }, this);
    return result.join("").trim().split("\n", 1)[0];
}
NodeFormat.prototype.formatOutput = function(spot, keepBlanks) {
    // return a list of formatted text output lines
    var line, numEmptyFields, numFullFields, text, match;
    var result = [];
    this.outputLines.forEach(function(lineData) {
        line = "";
        numEmptyFields = 0;
        numFullFields = 0;
        lineData.forEach(function(part) {
            if (typeof part.outputText === "function") {
                text = part.outputText(spot, false, this.formatHtml);
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
        if (keepBlanks || numFullFields > 0 || numEmptyFields == 0) {
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
    this.mathResultType = valueOrDefault(fieldData, "resulttype", "number");
    this.placeholder = false;
    this.ancestorLevel = 0;
    this.descendantLevel = 0;
    this.staticInfo = "";
    if (this.fieldType == "Numbering") {
        this.numberingFormats = initNumbering(this.format);
    }
    if (this.fieldType == "Choice" || this.fieldType == "Combination") {
        var formatText = this.format.replace(/\/\//g, "\0");
        if (valueOrDefault(fieldData, "evalhtml", false)) {
            formatText = escapeHtml(formatText);
        }
        this.choiceList = formatText.split("/").map(function(text) {
            return text.replace(/\0/g, "/");
        });
    }
}
FieldFormat.prototype.outputText = function(spot, titleMode, formatHtml) {
    // return formatted output text for this field in this node
    var splitValue, outputSep, selections, result, match, i, field;
    var newNodes, prevNodes;
    var value = valueOrDefault(spot.nodeRef.data, this.name, "");
    if (!value && !this.placeholder) return "";
    switch (this.fieldType) {
        case "OneLineText":
            value = value.split("<br />", 1)[0];
            break;
        case "SpacedText":
            value = "<pre>" + value + "</pre>";
            break;
        case "Number":
            var num = Number(value);
            value = formatNumber(num, this.format);
            break;
        case "Math":
            if (this.mathResultType == "number") {
                var num = Number(value);
                value = formatNumber(num, this.format);
            } else if (this.mathResultType == "date") {
                value = formatDate(value, this.format);
            } else if (this.mathResultType == "time") {
                value = formatTime(value, this.format);
            } else if (this.mathResultType == "boolean") {
                value = formatBoolean(value, this.format);
            }
            break;
        case "Numbering":
            value = formatNumbering(value, this.numberingFormats);
            break;
        case "Date":
            value = formatDate(value, this.format);
            break;
        case "Time":
            value = formatTime(value, this.format);
            break;
        case "DateTime":
            splitValue = value.split(" ");
            value = formatDate(splitValue[0], this.format);
            value = formatTime(splitValue[1], value);
            break;
        case "Choice":
            if (this.choiceList.indexOf(value) < 0) value = "#####";
            break;
        case "Combination":
            outputSep = spot.nodeRef.formatRef.outputSeparator;
            value = value.replace(/\/\//g, "\0");
            selections = value.split("/").map(function(text) {
                return text.replace(/\0/g, "/");
            });
            result = this.choiceList.filter(function(text) {
                return selections.indexOf(text) >= 0;
            });
            if (result.length == selections.length) {
                value = result.join(outputSep);
            } else {
                value = "#####";
            }
            break;
        case "AutoCombination":
            outputSep = spot.nodeRef.formatRef.outputSeparator;
            value = value.replace(/\/\//g, "\0");
            selections = value.split("/").map(function(text) {
                return text.replace(/\0/g, "/");
            });
            value = selections.join(outputSep);
            break;
        case "Boolean":
            value = formatBoolean(value, this.format);
            break;
        case "ExternalLink":
        case "InternalLink":
            if (titleMode) {
                match = /<a [^>]*href="([^"]+)"[^>]*>([\S\s]*?)<\/a>/i.
                        exec(value);
                if (match) {
                    value = match[2].trim();
                    if (!value) {
                        value = match[1];
                        if (value.startsWith("#")) value = value.substr(1);
                    }
                }
            }
            break;
        case "Picture":
            if (titleMode) {
                match = /<img [^>]*src="([^"]+)"[^>]*>/i.exec(value);
                if (match) value = match(1).trim();
            }
            break;
        case "RegularExpression":
            match = new RegExp(this.format).exec(unescapeHtml(value));
            if (!match || match[0] != unescapeHtml(value)) {
                value = "#####";
            }
            break;
        case "AncestorLevel":
            value = "";
            for (i = 0; i < this.ancestorLevel; i++) {
                spot = spot.parentSpot;
            }
            if (spot) {
                field = spot.nodeRef.formatRef.fieldDict[this.name];
                if (field) {
                    value = field.outputText(spot, titleMode, formatHtml);
                }
            }
            break;
        case "AnyAncestor":
            value = "";
            while (spot.parentSpot) {
                spot = spot.parentSpot;
                field = spot.nodeRef.formatRef.fieldDict[this.name];
                if (field) {
                    value = field.outputText(spot, titleMode, formatHtml);
                    break;
                }
            }
            break;
        case "ChildList":
            result = [];
            spot.childSpots().forEach(function(childSpot) {
                field = childSpot.nodeRef.formatRef.fieldDict[this.name];
                if (field) {
                    result.push(field.outputText(childSpot, titleMode,
                                                 formatHtml));
                }
            }, this);
            outputSep = spot.nodeRef.formatRef.outputSeparator;
            value = result.join(outputSep);
            break;
        case "DescendantCount":
            newNodes = [spot.nodeRef];
            for (i = 0; i < this.descendantLevel; i++) {
                prevNodes = newNodes;
                newNodes = [];
                prevNodes.forEach(function(child) {
                    newNodes = newNodes.concat(child.childList);
                });
            }
            value = newNodes.length.toString();
            break;
        case "StaticFileInfo":
            value = this.staticInfo;
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

function OutputItem(spot, level) {
    // class to store output for a single node
    var format = spot.nodeRef.formatRef;
    if (format.useTables) {
        this.textLines = format.formatOutput(spot, true);
    } else {
        this.textLines = format.formatOutput(spot, false).
                         map(function(line) {
            return line + "<br />";
        });
    }
    this.level = level;
    this.uId = spot.uId;
    this.addSpace = format.spaceBetween;
    this.siblingPrefix = format.siblingPrefix;
    this.siblingSuffix = format.siblingSuffix;
    if (format.useBullets && this.textLines.length > 0) {
        this.textLines[this.textLines.length - 1] =
             this.textLines[this.textLines.length - 1].slice(0, -6);
    }
}
OutputItem.prototype.addIndent = function(prevLevel, nextLevel) {
    // add <div> tags to define indent levels in the output
    var i;
    for (i = 0; i < this.level - prevLevel; i++) {
        this.textLines[0] = "<div>" + this.textLines[0];
    }
    for (i = 0; i < this.level - nextLevel; i++) {
        this.textLines[this.textLines.length - 1] += "</div>";
    }
}
OutputItem.prototype.addSiblingPrefix = function() {
    // add the sibling prefix before this output
    if (this.siblingPrefix) {
        this.textLines[0] = this.siblingPrefix + this.textLines[0];
    }
}
OutputItem.prototype.addSiblingSuffix = function() {
    // add the sibling suffix after this output
    if (this.siblingSuffix) {
        this.textLines[this.textLines.length - 1] += this.siblingSuffix;
    }
}
OutputItem.prototype.equalPrefix = function(otherItem) {
    // return true if sibling prefixes and suffixes are equal
    return (this.siblingPrefix == otherItem.siblingPrefix &&
            this.siblingSuffix == otherItem.siblingSuffix);
}

function OutputGroup() {
    // class to store and modify output lines
    this.itemList = [];
    if (selectedSpot) {
        this.itemList.push(new OutputItem(selectedSpot, 0));
        this.addChildren(selectedSpot, 0);
        if (this.hasPrefixes()) this.combineAllSiblings();
        this.addBlanksBetween();
        this.addIndents();
    }
}
OutputGroup.prototype.addChildren = function(spot, level) {
    // recursively add output items for descendants
    spot.childSpots().forEach(function(childSpot) {
        this.itemList.push(new OutputItem(childSpot, level + 1));
        this.addChildren(childSpot, level + 1);
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
OutputGroup.prototype.hasPrefixes = function() {
    // return true if sibling prefixes or suffixes are found
    var items = this.itemList.filter(function(item) {
        return item.siblingPrefix || item.siblingSuffix;
    });
    return items.length > 0;
}
OutputGroup.prototype.combineAllSiblings = function() {
    // group all sibling items with the same prefix into single items
    // also add sibling prefixes and suffixes and spaces in between
    var newItems = [];
    var prevItem = null;
    this.itemList.forEach(function(item) {
        if (prevItem) {
            if (item.level == prevItem.level && item.equalPrefix(prevItem)) {
                if (item.addSpace || prevItem.addSpace) {
                    prevItem.textLines[prevItem.textLines.length - 1] +=
                             "<br />";
                }
                prevItem.textLines = prevItem.textLines.concat(item.textLines);
            } else {
                prevItem.addSiblingSuffix();
                newItems.push(prevItem);
                item.addSiblingPrefix();
                prevItem = item;
            }
        } else {
            item.addSiblingPrefix();
            prevItem = item;
        }
    });
    prevItem.addSiblingSuffix();
    newItems.push(prevItem);
    this.itemList = newItems;
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
    var spot;
    if (event.target.tagName == "SPAN") {
        var elemId = event.target.parentElement.getAttribute("id");
        spot = spotDict[elemId];
        if (spot) {
            if (event.target.classList.contains("marker")) {
                spot.toggleOpen();
            } else if (event.target.classList.contains("nodetext")) {
                spot.select();
            }
        }
    } else if (event.target.tagName == "A") {
        var addr = event.target.getAttribute("href");
        if (addr.startsWith("#")) {
            event.preventDefault();
            spot = spotDict[addr.substr(1)];
            if (spot) {
                spot.openParents();
                spot.select();
            }
        }
    }
}

window.onkeydown = function(event) {
    // handle arrow keys for selection management
    var spot;
    switch (event.which) {
        case 38:  // up arrow
            if (selectedSpot) {
                spot = selectedSpot.prevTreeSpot();
            } else {
                spot = rootSpots[0];
            }
            if (spot) spot.select();
            event.preventDefault();
            break;
        case 40:  // down arrow
            if (selectedSpot) {
                spot = selectedSpot.nextTreeSpot();
            } else {
                spot = rootSpots[0];
            }
            if (spot) spot.select();
            event.preventDefault();
            break;
        case 37:  // left arrow
            if (selectedSpot && selectedSpot.open) selectedSpot.toggleOpen();
            event.preventDefault();
            break;
        case 39:  // right arrow
            if (selectedSpot && !selectedSpot.open) selectedSpot.toggleOpen();
            event.preventDefault();
            break;
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
    return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g,
                                                                     '&gt;');
}

function unescapeHtml(text) {
    // return the given string with &, <, > unescaped
    return text.replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g,
                                                                     ">");
}

function removeMarkup(text) {
    // return text with all HTML Markup removed and entities unescaped
    return text.replace(/<.*?>/g, "").replace(/&amp;/g, "&").
           replace(/&lt;/g, "<").replace(/&gt;/g, ">");
}

function formatNumber(num, format) {
    // return a formttted string for the given number
    var formatParts = format.split(/e/i);
    if (formatParts.length < 2) return formatBasicNumber(num, format);
    var formatMain = formatParts[0];
    var formatExp = formatParts[1];
    var exp = Math.floor(Math.log(Math.abs(num)) / Math.LN10);
    num = num / Math.pow(10, exp);
    var totalPlcs = (formatMain.match(/[#0]/g) || []).length;
    if (totalPlcs < 1) totalPlcs = 1;
    num = Number(num.toFixed(totalPlcs - 1));
    var radix = ".";
    if (format.indexOf("\\,") < 0 && (format.indexOf("\\.") >= 0 ||
                      (format.indexOf(",") >= 0 && format.indexOf(".") < 0))) {
        radix = ",";
    }
    var formatWhole = formatMain.split(radix)[0];
    var wholePlcs = (formatWhole.match(/[#0]/g) || []).length;
    var expChg = wholePlcs - Math.floor(Math.log(Math.abs(num)) / Math.LN10) -
                 1;
    num = num * Math.pow(10, expChg);
    exp -= expChg;
    var c = format.indexOf("e") >= 0 ? "e" : "E";
    return formatBasicNumber(num, formatMain) + c +
           formatBasicNumber(exp, formatExp)
}

function formatBasicNumber(num, format) {
    // return a formatted string for the given number without an exponent
    var radix;
    if (format.indexOf("\\,") < 0 && (format.indexOf("\\.") >= 0 ||
                      (format.indexOf(",") >= 0 && format.indexOf(".") < 0))) {
        radix = ",";
        format.replace(/\\./g, ".");
    } else {
        radix = ".";
        format.replace(/\\,/g, ",");
    }
    var formatParts = format.split(radix);
    var formatWhole = formatParts[0].split("");
    var formatFract = formatParts.length > 1 ? formatParts[1] : "";
    var decPlcs = (formatFract.match(/[#0]/g) || []).length;
    formatFract = formatFract.split("");
    var numParts = num.toFixed(decPlcs).split(".");
    var numWhole = numParts[0].split("");
    var numFract = numParts.length > 1 ? numParts[1] : "";
    numFract = numFract.replace(/0+$/g, "").split("");
    var sign = "+";
    if (numWhole[0] == "-") sign = numWhole.shift();
    var c;
    var result = [];
    while (numWhole.length || formatWhole.length) {
        c = formatWhole.length ? formatWhole.pop() : "";
        if (c && "#0 +-".indexOf(c) < 0) {
            if (numWhole.length || formatWhole.indexOf("0") >= 0) {
                result.unshift(c);
            }
        } else if (numWhole.length && c != " ") {
            result.unshift(numWhole.pop());
            if (c && "+-".indexOf(c) >= 0) {
                formatWhole.push(c);
            }
        } else if ("0 ".indexOf(c) >= 0) {
            result.unshift(c);
        } else if ("+-".indexOf(c) >= 0) {
            if (sign == "-" || c == "+") {
                result.unshift(sign);
            }
            sign = "";
        }
    }
    if (sign == "-") {
        if (result[0] == " ") {
            result = [result.join("").replace(/\s(?!\s)/, "-")];
        } else {
            result.unshift("-");
        }
    }
    if (formatFract.length || (format.length &&
                               format.charAt(format.length - 1) == radix)) {
        result.push(radix);
    }
    while (formatFract.length) {
        c = formatFract.shift();
        if ("#0 ".indexOf(c) <  0) {
            if (numFract.length || formatFract.indexOf("0") >= 0) {
                result.push(c);
            }
        } else if (numFract.length) {
            result.push(numFract.shift());
        } else if ("0 ".indexOf(c) >= 0) {
            result.push("0");
        }
    }
    return result.join("");
}

function initNumbering(format) {
    // return an array of basic numbering formats
    var sectionStyle = false;
    var tmpFormat = format.replace(/\.\./g, ".").replace(/\/\//g, "\0");
    var delim = "/";
    var formats = tmpFormat.split(delim);
    if (formats.length < 2) {
        tmpFormat = format.replace(/\/\//g, "/").replace(/\.\./g, "\0");
        delim = ".";
        formats = tmpFormat.split(delim);
        if (formats.length > 1) sectionStyle = true;
    }
    formats = formats.map(function(text) {
        return new NumberingFormat(text.replace(/\0/g, delim), sectionStyle);
    });
    return formats;
}

function NumberingFormat(formatStr, sectionStyle) {
    // class to store basic formatting for an element of numbering fields
    this.romanDict = {0: "", 1: "I", 2: "II", 3: "III", 4: "IV", 5: "V",
                      6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X",
                      20: "XX", 30: "XXX", 40: "XL", 50: "L", 60: "LX",
                      70: "LXX", 80: "LXXX", 90: "XC", 100: "C", 200: "CC",
                      300: "CCC", 400: "CD", 500: "D", 600: "DC",
                      700: "DCC", 800: "DCCC", 900: "CM", 1000: "M",
                      2000: "MM", 3000: "MMM"};
    this.sectionStyle = sectionStyle;
    var match = /(.*)([1AaIi])(.*)/.exec(formatStr);
    if (match) {
        this.prefix = match[1];
        this.format = match[2];
        this.suffix = match[3];
    } else {
        this.prefix = formatStr;
        this.format = "1";
        this.suffix = "";
    } 
}
NumberingFormat.prototype.numString = function(num) {
    var result = "";
    var digit;
    var factor = 1000;
    if (num > 0) {
        if (this.format == "1") {
            result = num.toString();
        } else if (this.format == "A" || this.format == "a") {
            while (num) {
                digit = (num - 1) % 26;
                result = String.fromCharCode(digit + "A".charCodeAt(0)) +
                         result;
                num = Math.floor((num - digit - 1) / 26);
            }
            if (this.format == "a") result = result.toLowerCase();
        } else if (num < 4000) {
            while (num) {
                digit = num - (num % factor);
                result += this.romanDict[digit];
                factor = Math.floor(factor / 10);
                num -= digit;
            }
            if (this.format == "i") result = result.toLowerCase();
        }
    }
    return this.prefix + result + this.suffix;
}

function formatNumbering(value, numFormats) {
    // return a formatted string for a numbering field
    var inputNums = value.split(".").map(function(num) {
        return Number(num);
    });
    if (numFormats[0].sectionStyle) {
        numFormats = numFormats.slice();
        while (numFormats.length < inputNums.length) {
            numFormats.push(numFormats[numFormats.length - 1]);
        }
        var results = inputNums.map(function(num, i) {
            return numFormats[i].numString(num);
        });
        return results.join(".");
    } else {
        var numFormat = numFormats[inputNums.length - 1];
        if (!numFormat) numFormat = numFormats[numFormats.length - 1];
        return numFormat.numString(inputNums[inputNums.length - 1]);
    }
}

function formatDate(storedText, format) {
    // return a formatted date string
    var monthNames = ["", "January", "February", "March", "April", "May",
                      "June", "July", "August", "September", "October",
                      "November", "December"];
    var dateArray = storedText.split("-");
    var year = dateArray[0];
    var month = dateArray[1];
    var day = dateArray[2];
    var yearNum = Number(year);
    var monthNum = Number(month);
    var dayNum = Number(day);
    format = format.replace(/%-d/g, dayNum).replace(/%d/g, day);
    format = format.replace(/%a/g, weekday(yearNum, monthNum,
                                           dayNum).substr(0, 3));
    format = format.replace(/%A/g, weekday(yearNum, monthNum, dayNum));
    format = format.replace(/%-m/g, monthNum).replace(/%m/g, month);
    format = format.replace(/%b/g, monthNames[monthNum].substr(0, 3));
    format = format.replace(/%B/g, monthNames[monthNum]);
    format = format.replace(/%y/g, year.slice(-2)).replace(/%Y/g, year);
    format = format.replace(/%-U/g, weekNumber(yearNum, monthNum, dayNum));
    format = format.replace(/%-j/g, dayOfYear(yearNum, monthNum, dayNum));
    return format;
}

function dayOfYear(year, month, day) {
    // return the day of year (1 to 366)
    var daysInMonths = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    var day = daysInMonths[month - 1] + day;
    if (month > 2 && year % 4 == 0 && (year % 100 != 0 || year % 400 == 0)) {
        day += 1;
    }
    return day;
}

function firstWeekday(year) {
    // return a number for the weekday of Jan. 1st (0=Sun., 6=Sat.)
    var y = year - 1;
    return (y + Math.floor(y / 4) - Math.floor(y / 100) + Math.floor(y / 400)
            + 1) % 7;
}

function weekday(year, month, day) {
    // return the weekday name for the given date
    var weekdays = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday"];
    var day = (firstWeekday(year) + dayOfYear(year, month, day) - 1) % 7;
    return weekdays[day];
}

function weekNumber(year, month, day) {
    // return the week number for the given date
    return Math.floor((dayOfYear(year, month, day) + firstWeekday(year) - 1)
                      / 7);
}

function formatTime(storedText, format) {
    // return a formatted time string
    var timeArray = storedText.split(":");
    var hour = timeArray[0];
    var minute = timeArray[1];
    var second = timeArray[2].split(".")[0];
    var microSecond = timeArray[2].split(".")[1];
    var hourNum = Number(hour);
    var minuteNum = Number(minute);
    var secondNum = Number(second);
    format = format.replace(/%-H/g, hourNum).replace(/%H/g, hour);
    var ampm = "AM";
    if (hourNum == 0) {
        hourNum = 12;
        hour = "12";
    } else if (hourNum > 11) {
        ampm = "PM";
        if (hourNum > 12) {
            hourNum -= 12;
            hour = hourNum.toString();
            if (hourNum < 10) hour = "0" + hour;
        }
    }
    format = format.replace(/%-I/g, hourNum).replace(/%I/g, hour);
    format = format.replace(/%-M/g, minuteNum).replace(/%M/g, minute);
    format = format.replace(/%-S/g, secondNum).replace(/%S/g, second);
    format = format.replace(/%f/g, microSecond).replace(/%p/g, ampm);
    return format;
}

function formatBoolean(storedText, format) {
    // return a formatted boolean string
    var boolDict = {"true": 0, "false": 1, "t": 0, "f": 1,
                    "yes": 0, "no": 1, "y": 0, "n": 1};
    var valueNum = boolDict[storedText.toLowerCase()];
    var value = format.split("/")[valueNum];
    if (value == undefined) value = "#####";
    return value;
}

main();
