"use strict";

var nodeDict = {};
var rootNodes = [];
var treeFormats = {};
var selectedId = "";

var dataSource = "http://mail.bellz.org/data/MiscInfo.trln";
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
            var formatName;
            for (formatName in fileData.formats) {
                treeFormats[formatName] = new NodeFormat(fileData.
                                                         formats[formatName]);
            }
            var node;
            fileData.nodes.forEach(function(nodeData) {
                node = new TreeNode(nodeData);
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

function TreeNode(fileData) {
    // class to store nodes
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
    textSpan.appendChild(document.createTextNode(this.data["Name"]));
    textSpan.className = "nodetext";
    element.appendChild(textSpan);
    element.setAttribute("id", this.uId);
    parentElement.appendChild(element);
    if (this.open && this.childList.length > 0) {
        this.openChildren(element);
    }
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
    if (this.childList.length == 0) {
        return;
    }
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
    var that = this;
    formatData.fields.forEach(function(fieldData) {
        that.fieldDict[fieldData.fieldname] = new FieldFormat(fieldData);
    });
    this.titleLine = [formatData.titleline];
    this.outputLines = [];
    formatData.outputlines.forEach(function(outputLine) {
        that.outputLines.push([outputLine]);
    });
}

function FieldFormat(fieldData) {
    // class to store field format data and format field output
    this.name = fieldData.fieldname;
    this.fieldType = fieldData.fieldtype;
}
NodeFormat.prototype.outputText = function(node, titleMode, formatHtml) {
    // return formatted output text for this field in this node
    var value = node.data[this.name];
    if (value === undefined) {
        value = "";
    }
    return value;
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
            }
        }
    }
}
