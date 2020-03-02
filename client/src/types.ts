import { UploadType } from 'multinet';

export interface KeyValue {
  key: string;
  value: any;
}

export interface TableRow {
  _key: string;
  _id: string;
  _rev: string;
  [key: string]: any;
}

export interface FileType {
  displayName: string;
  hint: string;
  extension: string[];
  queryCall: UploadType;
}

export interface FileTypeTable {
  [key: string]: FileType;
}
