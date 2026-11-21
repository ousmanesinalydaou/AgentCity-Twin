import { readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";
import bm from "@/i18n/bm.json";
import fr from "@/i18n/fr.json";

function sources(directory:string):string[] {
  return readdirSync(directory,{withFileTypes:true}).flatMap(item=>{
    const path=resolve(directory,item.name);
    return item.isDirectory()?sources(path):item.name.endsWith(".tsx")?[path]:[];
  });
}
function literalLabels(ast:ts.SourceFile) {
  const labels:string[]=[];
  function read(node:ts.Expression) {
    if(ts.isStringLiteralLike(node)) labels.push(node.text);
    else if(ts.isConditionalExpression(node)){read(node.whenTrue);read(node.whenFalse);}
  }
  function scan(node:ts.Node) {
    if(ts.isCallExpression(node)&&ts.isIdentifier(node.expression)&&node.expression.text==="t"&&node.arguments[0])read(node.arguments[0]);
    ts.forEachChild(node,scan);
  }
  scan(ast);
  return labels;
}

describe("authored interface catalogs",()=>{
  it("defines French and Bambara strings for each literal localization key",()=>{
    const keys=new Set(sources(resolve(process.cwd(),"src")).flatMap(file=>
      literalLabels(ts.createSourceFile(file,readFileSync(file,"utf8"),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX))));
    for(const messages of [fr,bm]) {
      expect([...keys].filter(key=>!Object.hasOwn(messages,key)).sort()).toEqual([]);
    }
  });
});

